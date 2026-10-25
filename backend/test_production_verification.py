import asyncio
import json
import os
import sys
from pathlib import Path
import httpx

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.models.segment import IsochronicSegment
from app.services.translator import isochronic_translator
from app.services.voice_synthesis import voice_synthesis_engine
from app.services.lipsync_engine import lipsync_engine
from app.services.media_engine import media_engine


async def main():
    print("=================================================================")
    print("MASTER PRODUCTION OVERHAUL: END-TO-END VERIFICATION")
    print("Target Video: 1:38 SRM University Tech Self-Intro")
    print("=================================================================")

    # 1. Fetch segments
    async with httpx.AsyncClient() as client:
        res = await client.get("http://127.0.0.1:8000/api/v1/projects/2f230119-9d1d-4377-bbcc-d84c78d33940/status")
        data = res.json()
        segments_raw = data["segments"]

    segments = [IsochronicSegment(**s) for s in segments_raw]
    print(f"Loaded {len(segments)} ASR segments from original video.")

    out_dir = BASE_DIR / "app/storage/master_verification_output"
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    master_mixed = audio_dir / "master_mixed.wav"

    # Step 1: Translation with Gemini
    translated_cache = out_dir / "gemini_translated_segments.json"
    if translated_cache.exists():
        print(f"\n[Step 1] Loading cached Gemini Telugish translations from {translated_cache.name}...")
        with open(translated_cache, "r") as f:
            t_data = json.load(f)
        translated_segments = [IsochronicSegment(**s) for s in t_data]
    else:
        print("\n[Step 1] Translating with Gemini (Code-Switched 'Telugish' with English Tech Terms)...")
        translated_segments = await isochronic_translator.translate_all_segments(segments, "te")
        with open(translated_cache, "w") as f:
            json.dump([s.model_dump() for s in translated_segments], f, indent=2, ensure_ascii=False)

    print(f"Translation complete for all {len(translated_segments)} segments!")
    stiff_count = sum(1 for s in translated_segments if "మరియు" in s.target_text)
    print(f"Stiff 'మరియు' occurrences: {stiff_count} (Must be 0)")

    # Step 2: Speaker Profiling
    vocal_ref = BASE_DIR / "app/storage/audio_segments/2f230119-9d1d-4377-bbcc-d84c78d33940/vocals_16k.wav"
    speaker_prof = voice_synthesis_engine.profile_speaker(vocal_ref)
    print(f"\n[Step 2] Speaker Profile from vocals.wav: {speaker_prof}")

    # Step 3: Synthesis check
    all_aligned_exist = all((audio_dir / f"aligned_{s.segment_id}.wav").exists() for s in translated_segments)
    if master_mixed.exists() and all_aligned_exist:
        print(f"\n[Step 3 & 4] Master mixed audio already assembled ({master_mixed.stat().st_size} bytes).")
    else:
        print("\n[Step 3] Synthesizing speech with te-IN-MohanNeural & Dynamic Time-Alignment...")
        aligned_pairs = []
        for s in translated_segments:
            synth_file = audio_dir / f"synth_{s.segment_id}.wav"
            aligned_file = audio_dir / f"aligned_{s.segment_id}.wav"

            await voice_synthesis_engine.synthesize_segment(
                text=s.target_text,
                reference_audio_path=vocal_ref,
                target_lang="te",
                output_path=synth_file,
                target_duration_sec=s.duration_budget,
            )

            voice_synthesis_engine.align_audio_duration(
                input_audio_path=synth_file,
                target_duration_sec=s.duration_budget,
                output_path=aligned_file,
            )
            aligned_pairs.append((s, aligned_file))

        print("\n[Step 4] Assembling Master Dialogue Timeline & Mixing...")
        total_dur = 98.82
        master_dialogue = audio_dir / "master_dialogue.wav"
        voice_synthesis_engine.build_master_dialogue_timeline(
            aligned_segments=aligned_pairs,
            total_duration_sec=total_dur,
            output_path=master_dialogue,
        )

        bg_path = BASE_DIR / "app/storage/audio_segments/2f230119-9d1d-4377-bbcc-d84c78d33940/background.wav"
        voice_synthesis_engine.mix_master_audio(
            dialogue_path=master_dialogue,
            background_ambient_path=bg_path,
            output_path=master_mixed,
        )
        print(f"Master mixed audio rendered at: {master_mixed} ({master_mixed.stat().st_size} bytes)")

    # Step 5: Zero-Damage Lip-Sync
    print("\n[Step 5] Executing Zero-Damage Lip-Sync with resting-lip silence suppression...")
    silent_vid = BASE_DIR / "app/storage/outputs/2f230119-9d1d-4377-bbcc-d84c78d33940/2f230119-9d1d-4377-bbcc-d84c78d33940_Movie on 05-10-26 at 8.48 AM_lossless_silent.mp4"
    if not silent_vid.exists():
        # Fallback to search if filename has slight character difference
        candidates = list((BASE_DIR / "app/storage/outputs/2f230119-9d1d-4377-bbcc-d84c78d33940").glob("*lossless_silent.mp4"))
        if candidates:
            silent_vid = candidates[0]
    print(f"Using silent video stream: {silent_vid} (exists={silent_vid.exists()})")

    synced_vid = out_dir / "synced_silent.mp4"

    def progress_cb(cur, tot):
        if cur % 300 == 0 or cur == tot:
            print(f"  Lip-sync frame {cur}/{tot} ({cur/tot*100:.1f}%)")

    await lipsync_engine.sync_lips_async(
        silent_video_path=silent_vid,
        aligned_audio_path=master_mixed,
        output_synced_video_path=synced_vid,
        progress_callback=progress_cb,
    )
    print(f"Lip-sync video rendered at: {synced_vid} ({synced_vid.stat().st_size} bytes)")

    # Step 6: Remux final video
    print("\n[Step 6] Remuxing Final High-Fidelity Video (CRF 18 fast, AAC 320k)...")
    final_dubbed = out_dir / "final_dubbed_telugu_master.mp4"
    media_engine.remux_final_video(
        synced_video_path=synced_vid,
        mixed_audio_path=master_mixed,
        output_final_path=final_dubbed,
    )
    print(f"\nSUCCESS! Master Final dubbed video rendered at:")
    print(f"  {final_dubbed} ({final_dubbed.stat().st_size / (1024*1024):.2f} MB)")

    # Step 7: Print side-by-side verification table
    print("\n=================================================================")
    print("VERIFICATION RESULTS (ALL 24 SEGMENTS)")
    print("=================================================================")
    for s in translated_segments:
        print(f"[{s.start_time:05.2f}s - {s.end_time:05.2f}s] (Budget: {s.duration_budget:.2f}s | Aksharas: {s.target_syllables} | Ratio: {s.pacing_ratio:.2f})")
        print(f"  EN: {s.source_text}")
        print(f"  TE: {s.target_text}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
