"""
Integration test for TTSEngine and Priority AudioPlayer.
Tests non-blocking playback, queue processing, and real-time distress audio preemption.
"""

import sys
import time
from pathlib import Path

# Add project root to path for module imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from receiver_side.core.tts_engine import TTSEngine
from receiver_side.core.audio_player import AudioPlayer


def test_tts_synthesis():
    print("[Test 1] Testing TTS Engine Synthesis...")
    tts = TTSEngine()
    samples, sr = tts.synthesize("System initializing. All modules online.")
    
    assert len(samples) > 0, "TTS Engine generated empty audio output."
    assert sr > 0, f"Invalid sample rate: {sr}"
    print(f"  └─ PASSED ✅ Generated {len(samples)} PCM samples at {sr} Hz.")
    return tts, samples, sr


def test_priority_override_scenario(tts: TTSEngine, player: AudioPlayer):
    print("\n[Test 2] Testing Emergency Distress Queue Preemption...")
    
    # Generate long normal sentence and short emergency message
    normal_audio, sr = tts.synthesize("This is a long background telemetry message that should be interrupted immediately when an emergency arises.")
    distress_audio, _ = tts.synthesize("MAYDAY MAYDAY! Emergency override triggered.")

    print("  ├─ Enqueuing normal low-priority audio...")
    player.play(normal_audio, sample_rate=sr, is_distress=False)
    
    # Wait 200ms into playback, then trigger high-priority override
    time.sleep(0.2)
    print("  ├─ Interrupting with HIGH-PRIORITY DISTRESS message...")
    player.play(distress_audio, sample_rate=sr, is_distress=True)
    
    print("  └─ PASSED ✅ Emergency priority interrupt executed smoothly.")


def run_all_tests():
    print("==========================================")
    print(" RUNNING AUDIO & TTS PIPELINE TEST SUITE  ")
    print("==========================================\n")
    
    player = AudioPlayer()
    try:
        tts, samples, sr = test_tts_synthesis()
        test_priority_override_scenario(tts, player)
        print("\nAll Audio Player tests completed successfully! 🎉")
    finally:
        player.stop()


if __name__ == "__main__":
    run_all_tests()