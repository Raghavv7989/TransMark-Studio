#!/usr/bin/env python3
"""
Mission 3 Live End-to-End Verification Script:
1. Uploads video for Telugu ('te') localization
2. Waits for Demuxing, ASR, and Isochronic Translation
3. Triggers POST /api/v1/projects/{job_id}/synthesize
4. Streams live WebSocket progress through:
   - CLONING_VOICE (Segment synthesis & dynamic duration alignment)
   - LIP_SYNCING (Zero-damage mouth synthesis & CodeFormer restoration)
   - REMUXING (FFmpeg visually lossless CRF 18 render)
   - COMPLETED
5. Downloads and probes finalized dubbed video artifacts.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
import httpx
import websockets

import os

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
SERVER_PORT = os.getenv("BACKEND_PORT", os.getenv("PORT", "8000"))
API_BASE = f"http://127.0.0.1:{SERVER_PORT}/api/v1"
WS_BASE = f"ws://127.0.0.1:{SERVER_PORT}"


def generate_video(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=640x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


async def main():
    test_video = BACKEND_DIR / "app" / "storage" / "test_verification" / "mission3_source.mp4"
    print("=" * 70)
    print("TransMark Mission 3: Voice Cloning, Time-Alignment & Zero-Damage Lip-Sync")
    print("=" * 70)
    print(f"[*] Generating test video (2s @ 30fps = 60 frames) at {test_video}...")
    generate_video(test_video)

    # 1. Upload video
    target_lang = "te"
    print(f"\n[1] Uploading video to {API_BASE}/projects/upload (target_language={target_lang})...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(test_video, "rb") as f:
            files = {"file": ("mission3_source.mp4", f, "video/mp4")}
            data = {"target_language": target_lang}
            res = await client.post(f"{API_BASE}/projects/upload", files=files, data=data)
            assert res.status_code == 202, f"Upload failed: {res.text}"
            upload_data = res.json()

    job_id = upload_data["job_id"]
    ws_url = f"{WS_BASE}{upload_data['ws_url']}"
    print(f"[+] Job initialized: {job_id}")

    # 2. Stream Phase 1-3 progress via WebSocket
    print(f"\n[2] Connecting to WebSocket stream {ws_url}...")
    async with websockets.connect(ws_url) as ws:
        while True:
            msg_text = await ws.recv()
            evt = json.loads(msg_text)
            status = evt.get("status")
            progress = evt.get("progress")
            subtask = evt.get("subtask")
            print(f"    --> [{status}] {progress}%: {subtask}")

            if status == "CURATING_TRANSLATION" and progress >= 70.0:
                print("\n[+] Phase 1-3 Complete: Translation ready for synthesis!")
                break
            elif status == "FAILED":
                print(f"[!] Pipeline failed: {evt.get('error')}")
                sys.exit(1)

    # 3. Trigger Synthesis via POST /projects/{job_id}/synthesize
    print(f"\n[3] Triggering POST {API_BASE}/projects/{job_id}/synthesize...")
    async with httpx.AsyncClient(timeout=15.0) as client:
        synth_res = await client.post(f"{API_BASE}/projects/{job_id}/synthesize")
        assert synth_res.status_code == 202, f"Synthesize call failed: {synth_res.text}"
        synth_data = synth_res.json()
        print(f"[+] Synthesis initiated: {synth_data['message']}")

    # 4. Stream Phase 4-6 progress via WebSocket
    print(f"\n[4] Monitoring Synthesis WebSocket Stream...")
    async with websockets.connect(ws_url) as ws:
        while True:
            msg_text = await ws.recv()
            evt = json.loads(msg_text)
            status = evt.get("status")
            progress = evt.get("progress")
            subtask = evt.get("subtask")
            print(f"    --> [{status}] {progress}%: {subtask}")

            if status == "COMPLETED":
                print("\n[+] SUCCESS: Full pipeline completed!")
                details = evt.get("details", {})
                final_vid_path = details.get("final_video")
                master_aud_path = details.get("master_audio")
                print(f"    Final Dubbed Video: {final_vid_path}")
                print(f"    Master Mixed Audio: {master_aud_path}")
                break
            elif status == "FAILED":
                print(f"[!] Synthesis failed: {evt.get('error')}")
                sys.exit(1)

    # 5. Download and verify artifacts
    print(f"\n[5] Downloading artifacts from API...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        vid_res = await client.get(f"{API_BASE}/projects/{job_id}/artifacts/final_video")
        assert vid_res.status_code == 200, "Failed to download final_video"
        aud_res = await client.get(f"{API_BASE}/projects/{job_id}/artifacts/master_audio")
        assert aud_res.status_code == 200, "Failed to download master_audio"

    saved_vid = BACKEND_DIR / "app" / "storage" / "test_verification" / "downloaded_final.mp4"
    saved_vid.write_bytes(vid_res.content)
    print(f"[+] Downloaded final dubbed video ({len(vid_res.content)} bytes) to {saved_vid.name}")

    # 6. Probe downloaded video with FFprobe
    print(f"\n[6] Probing final video properties...")
    from app.services.media_engine import media_engine
    meta = media_engine.probe_metadata(saved_vid)
    print(f"    - Resolution:       {meta.width}x{meta.height}")
    print(f"    - FPS:              {meta.fps}")
    print(f"    - Total Frames:     {meta.total_frames} (Zero dropped frames!)")
    print(f"    - Video Codec:      {meta.video_codec}")
    print(f"    - Has Audio:        {meta.has_audio} ({meta.audio_codec} @ {meta.audio_sample_rate}Hz)")

    assert meta.width == 640 and meta.height == 360, "Resolution mismatch!"
    assert meta.total_frames == 60, f"Frame count mismatch! Expected 60, got {meta.total_frames}"
    assert meta.has_audio is True, "Final video must contain mixed dubbed audio!"

    print("\n" + "=" * 70)
    print("MISSION 3 VERIFICATION COMPLETED WITH 100% ACCURACY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
