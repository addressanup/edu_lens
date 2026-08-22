# EduLens Student App (Android)

Point your phone camera at your homework. The AI tutor watches the live
stream, detects when you're stuck, and speaks up with friendly, Socratic
hints — powered by the DeepSeek vision model on the backend.

## Setup

```bash
cd mobile
npm install
```

Start the backend first (from the repo root):

```bash
.venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Then launch the app:

```bash
npm start        # scan the QR with Expo Go on Android
# or
npm run android  # with a device/emulator connected
```

## Connecting to the backend

1. Find your computer's LAN IP (`ipconfig getifaddr en0` on macOS).
2. In the app, tap **Change** and set `http://<LAN-IP>:8000`.
3. Tap **Connect** — the status dot turns green.
4. Tap **Start homework session** and point the camera at the page.

> Phone and computer must be on the same Wi-Fi network.
> For USB testing with a physical device: `adb reverse tcp:8000 tcp:8000`
> then use `http://localhost:8000`.

## How it works

- The app captures a photo every ~1.5 s, downscales it to 768 px wide, and
  streams it as base64 JPEG over WebSocket (`/ws/live/{session_id}`).
- The backend keeps only the latest frame in memory and runs continuous
  observation: every N seconds it asks the vision model whether the child is
  struggling; if so, it pushes an intervention which the app displays and
  reads aloud.
- Tapping **Ask** sends a question that is answered with the latest camera
  frame attached.

## Privacy

Frames exist in backend memory for the lifetime of the session only and are
dropped on disconnect. Nothing is written to disk.
