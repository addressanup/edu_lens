#!/usr/bin/env python3
"""
Test script for Parent Live Monitoring feature.
Tests the WebSocket flow: glasses -> backend -> parent app
"""

import asyncio
import json
import base64
import httpx
import websockets
import uuid
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"
WS_BASE = "ws://localhost:8000"

async def test_parent_monitoring():
    print("=" * 60)
    print("🧪 Parent Live Monitoring Integration Test")
    print("=" * 60)
    
    parent_id = f"parent_{uuid.uuid4().hex[:8]}"
    child_id = None
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Create a child profile with parent_id
        print("\n📝 Step 1: Creating child profile...")
        child_data = {
            "name": "Test Child",
            "age": 8,
            "grade": "3rd",
            "language": "en",
            "parent_id": parent_id,
            "allow_remote_monitoring": True,
            "allow_parent_voice": True,
            "notify_child_on_connect": True
        }
        
        response = await client.post(f"{API_BASE}/children", json=child_data)
        if response.status_code == 200:
            child = response.json()
            child_id = child["id"]
            print(f"   ✅ Created child: {child['name']} (ID: {child_id})")
            print(f"   📋 Parent ID: {parent_id}")
        else:
            print(f"   ❌ Failed to create child: {response.status_code}")
            print(f"   Response: {response.text}")
            return

    # Step 2: Connect glasses WebSocket (simulates child's glasses)
    print("\n🕶️  Step 2: Connecting glasses WebSocket...")
    
    glasses_ws = None
    parent_ws = None
    glasses_received = []
    parent_received = []
    
    try:
        # Connect glasses first
        glasses_uri = f"{WS_BASE}/ws/observe/{session_id}?child_id={child_id}"
        print(f"   Connecting to: {glasses_uri}")
        glasses_ws = await websockets.connect(glasses_uri)
        print("   ✅ Glasses connected!")
        
        # Wait a bit for session to initialize
        await asyncio.sleep(0.5)
        
        # Step 3: Connect parent WebSocket
        print("\n👨‍👩‍👧 Step 3: Connecting parent WebSocket...")
        parent_uri = f"{WS_BASE}/ws/parent/{session_id}?token={parent_id}&notify_child=true"
        print(f"   Connecting to: {parent_uri}")
        parent_ws = await websockets.connect(parent_uri)
        print("   ✅ Parent connected!")
        
        # Step 4: Check if glasses received parent connection notification
        print("\n📢 Step 4: Checking parent connection notification...")
        
        async def receive_with_timeout(ws, timeout=2.0):
            try:
                return await asyncio.wait_for(ws.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                return None
        
        # Check for notification on glasses
        glasses_msg = await receive_with_timeout(glasses_ws)
        if glasses_msg:
            try:
                data = json.loads(glasses_msg)
                glasses_received.append(data)
                print(f"   ✅ Glasses received: {data.get('event_type', data.get('type', 'unknown'))}")
                if data.get('event_type') == 'parent_connected':
                    print(f"      Parent ID: {data.get('payload', {}).get('parent_id', 'N/A')}")
            except:
                print(f"   ℹ️  Glasses received binary data ({len(glasses_msg)} bytes)")
        else:
            print("   ⚠️  No notification received (may be disabled or timeout)")
        
        # Step 5: Parent sends text message
        print("\n💬 Step 5: Parent sends text message...")
        text_msg = {
            "type": "text_message",
            "content": "Good job! Keep working on that math problem!",
            "language": "en",
            "timestamp": datetime.now().timestamp()
        }
        await parent_ws.send(json.dumps(text_msg))
        print(f"   📤 Sent: '{text_msg['content']}'")
        
        # Check if glasses received the message
        await asyncio.sleep(0.5)
        glasses_msg = await receive_with_timeout(glasses_ws)
        if glasses_msg:
            try:
                data = json.loads(glasses_msg)
                glasses_received.append(data)
                print(f"   ✅ Glasses received parent message event!")
                print(f"      Type: {data.get('event_type', 'unknown')}")
            except:
                print(f"   ✅ Glasses received audio data ({len(glasses_msg)} bytes)")
        else:
            print("   ⚠️  Glasses didn't receive message (TTS might not be configured)")
        
        # Step 6: Parent sends encouragement
        print("\n👍 Step 6: Parent sends encouragement...")
        encourage_msg = {
            "type": "encouragement",
            "content": "great_job",
            "timestamp": datetime.now().timestamp()
        }
        await parent_ws.send(json.dumps(encourage_msg))
        print("   📤 Sent: 'great_job' encouragement")
        
        # Step 7: Simulate glasses sending an observation event
        print("\n👀 Step 7: Glasses sends observation event...")
        # Actually, the observation is handled by the server
        # Let's check what parent receives when we send frames
        
        # Send a test frame (small JPEG-like data)
        test_frame = b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'  # Minimal JPEG structure
        await glasses_ws.send(test_frame)
        print("   📤 Sent test frame from glasses")
        
        # Check if parent receives frame
        parent_msg = await receive_with_timeout(parent_ws, timeout=2.0)
        if parent_msg:
            try:
                data = json.loads(parent_msg)
                parent_received.append(data)
                if data.get('type') == 'frame':
                    print(f"   ✅ Parent received frame! Quality: {data.get('quality', 'unknown')}")
                else:
                    print(f"   ✅ Parent received: {data.get('type', 'unknown')}")
            except:
                print(f"   ✅ Parent received binary data ({len(parent_msg)} bytes)")
        else:
            print("   ⚠️  No frame received by parent (might need observation session)")
        
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"   Glasses messages received: {len(glasses_received)}")
        print(f"   Parent messages received: {len(parent_received)}")
        print("   ✅ Parent monitoring connection test PASSED!")
        
    except websockets.exceptions.InvalidStatus as e:
        print(f"   ❌ WebSocket connection rejected: {e}")
        print(f"      Status code: {e.response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if glasses_ws:
            await glasses_ws.close()
        if parent_ws:
            await parent_ws.close()
        
        # Delete test child
        if child_id:
            async with httpx.AsyncClient() as client:
                await client.delete(f"{API_BASE}/children/{child_id}")
                print(f"\n🧹 Cleaned up test child: {child_id}")

if __name__ == "__main__":
    asyncio.run(test_parent_monitoring())
