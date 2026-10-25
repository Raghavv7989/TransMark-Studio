#!/usr/bin/env python3
"""
Live E2E Verification Script for Missions 1 & 2:
1. Upload video with target language (e.g. 'te' - Telugu)
2. Stream real-time WebSocket progress through SEPARATING_AUDIO, TRANSCRIBING, CURATING_TRANSLATION
3. Fetch time-coded segments via GET /api/v1/projects/{job_id}/segments
4. Test human curation and syllable recalculation via PUT /api/v1/projects/{job_id}/segments
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
SERVER_PORT = os.getenv("BACKEND_PORT", os.getenv("PORT", "8000"))
API_BASE = f"http://127.0.0.1:{SERVER_PORT}/api/v1"
WS_BASE = f"ws://127.0.0.1:{SERVER_PORT}"


def generate_video(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=480x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=500:duration=3:sample_rate=44100",
        "-c:v", "libx264", "-c:a", "aac",
        str(path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


async def main():
    test_video = BACKEND_DIR / "app" / "storage" / "test_verification" / "mission2_test_video.mp4"
    print(f"[*] Generating test video at {test_video}...")
    generate_video(test_video)

    # 1. Upload video specifying target_language="te"
    target_lang = "te"
    print(f"[*] Uploading video to {API_BASE}/projects/upload (target_language={target_lang})...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(test_video, "rb") as f:
            files = {"file": ("mission2_test_video.mp4", f, "video/mp4")}
            data = {"target_language": target_lang}
            res = await client.post(f"{API_BASE}/projects/upload", files=files, data=data)
            assert res.status_code == 202, f"Upload failed: {res.text}"
            upload_data = res.json()

    job_id = upload_data["job_id"]
    ws_path = upload_data["ws_url"]
    ws_url = f"{WS_BASE}{ws_path}"
    print(f"[+] Job created: {job_id}")
    print(f"[*] Connecting to WebSocket: {ws_url}...")

    # 2. Listen to WebSocket stream
    async with websockets.connect(ws_url) as ws:
        print("[+] WebSocket connected. Streaming pipeline stages...")
        while True:
            msg_text = await ws.recv()
            evt = json.loads(msg_text)
            status = evt.get("status")
            progress = evt.get("progress")
            subtask = evt.get("subtask")
            print(f"    --> [{status}] {progress}%: {subtask}")

            if status == "COMPLETED" or (status == "CURATING_TRANSLATION" and progress >= 70.0):
                print(f"\n[+] SUCCESS: Pipeline reached {status} ({progress}%)!")
                break
            elif status == "FAILED":
                print(f"\n[!] FAILED: Job failed with error: {evt.get('error')}")
                sys.exit(1)

    # 3. Test Human-in-the-Loop Curation GET endpoint
    print(f"\n[*] Testing GET {API_BASE}/projects/{job_id}/segments...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        get_res = await client.get(f"{API_BASE}/projects/{job_id}/segments")
        assert get_res.status_code == 200, f"GET segments failed: {get_res.text}"
        segments_data = get_res.json()

    print(f"[+] Retrieved {segments_data['total_segments']} segments for target language '{segments_data['target_language']}'.")
    for s in segments_data["segments"]:
        print(f"    - Segment #{s['segment_id']}: [{s['start_time']}s - {s['end_time']}s] (Budget: {s['duration_budget']}s)")
        print(f"      Source:    \"{s['source_text']}\" ({s['original_syllables']} syll)")
        print(f"      Target:    \"{s['target_text']}\" ({s['target_syllables']} syll)")
        print(f"      Phonetic:  \"{s['phonetic_text']}\"")
        print(f"      Fit Status: {s['fit_status']} (Pacing Ratio: {s['pacing_ratio']:.2f}, Deviation: {s['tolerance_pct']}%)")

    # 4. Test Human-in-the-Loop Curation PUT endpoint (Edit words & recalculate fit)
    print(f"\n[*] Testing PUT {API_BASE}/projects/{job_id}/segments (simulating frontend curator)...")
    curated_target = "అందరికీ మళ్ళీ స్వాగతం"
    curated_phonetic = "Andhariki malli swagatham"

    async with httpx.AsyncClient(timeout=10.0) as client:
        put_payload = {
            "segments": [
                {
                    "segment_id": 1,
                    "target_text": curated_target,
                    "phonetic_text": curated_phonetic,
                }
            ]
        }
        put_res = await client.put(f"{API_BASE}/projects/{job_id}/segments", json=put_payload)
        assert put_res.status_code == 200, f"PUT segments failed: {put_res.text}"
        put_data = put_res.json()

    print(f"[+] Curated segment updated: {put_data['message']}")
    curated_seg = put_data["segments"][0]
    print(f"    - Target Text:      \"{curated_seg['target_text']}\"")
    print(f"    - Phonetic Script:  \"{curated_seg['phonetic_text']}\"")
    print(f"    - Target Syllables: {curated_seg['target_syllables']}")
    print(f"    - Recalculated Fit: {curated_seg['fit_status']} (Pacing: {curated_seg['pacing_ratio']})")
    print("\n" + "=" * 70)
    print("MISSION 2 E2E VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
