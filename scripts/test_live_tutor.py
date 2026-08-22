#!/usr/bin/env python3
"""
E2E smoke test for the live tutoring WebSocket.

Streams synthetic "homework" frames to /ws/live/{session_id}, asks a question,
and prints every event the backend pushes. Requires a valid DEEPSEEK_API_KEY
in .env for the AI calls to succeed.

Usage:
    .venv/bin/python scripts/test_live_tutor.py [--server ws://localhost:8000]
"""

import argparse
import asyncio
import base64
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import websockets  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def make_homework_frame(text: str) -> str:
    """Render a simple homework page as base64 JPEG."""
    img = Image.new("RGB", (640, 400), "white")
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "Homework - Math", fill="black")
    draw.text((40, 120), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode()


async def run(server: str) -> None:
    uri = f"{server}/ws/live/smoke-{int(asyncio.get_event_loop().time())}"
    print(f"Connecting to {uri} ...")

    async with websockets.connect(uri) as ws:
        greeting = json.loads(await ws.recv())
        print(f"[{greeting['type']}] vision_model={greeting['payload'].get('vision_model')}")

        # Configure child profile
        await ws.send(json.dumps({"type": "config", "config": {"child_name": "TestChild", "child_age": 9}}))
        event = json.loads(await ws.recv())
        print(f"[{event['type']}] {event['payload']}")

        # Stream a few frames
        for i in range(3):
            frame = make_homework_frame("Problem 1: 24 / 6 = ___")
            await ws.send(json.dumps({"type": "frame", "data": frame, "width": 640, "height": 400}))
            await asyncio.sleep(0.2)
        print("[client] 3 frames sent")

        # Start continuous observation
        await ws.send(json.dumps({"type": "start_observation"}))
        event = json.loads(await ws.recv())
        print(f"[{event['type']}] {event['payload']}")

        # Ask an on-demand question
        await ws.send(json.dumps({"type": "query", "text": "I'm stuck on problem 1"}))
        print("[client] query sent: 'I'm stuck on problem 1'")

        # Collect events for ~20s (observation interval default is 12s)
        print("\n--- Listening for backend events (20s) ---")
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=20)
                event = json.loads(raw)
                payload = event.get("payload", {})
                if event["type"] == "observation":
                    print(
                        f"[observation] struggle={payload.get('struggle_detected')} "
                        f"conf={payload.get('confidence')} "
                        f"scene={str(payload.get('scene'))[:60]} "
                        f"intervention={str(payload.get('intervention'))[:80]}"
                    )
                elif event["type"] == "tutor_response":
                    print(f"[tutor_response] {payload.get('text')}")
                elif event["type"] == "error":
                    print(f"[error] {payload.get('message')}")
                else:
                    print(f"[{event['type']}] {json.dumps(payload)[:100]}")
        except asyncio.TimeoutError:
            pass

        # Stop and close
        await ws.send(json.dumps({"type": "stop_observation"}))
        try:
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            print(f"[{event['type']}] done")
        except asyncio.TimeoutError:
            pass

    print("\nSmoke test complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="ws://localhost:8000")
    args = parser.parse_args()
    asyncio.run(run(args.server))
