from pathlib import Path
from typing import List, Optional

try:
    from src.models import TranscriptSegment
except ModuleNotFoundError:
    from models import TranscriptSegment  # type: ignore[no-redef]


def transcribe_audio(audio_path: Optional[str]) -> List[TranscriptSegment]:
    """Transcribes lecture audio into timestamped transcript segments.
    Returns empty list if audio is None, missing, corrupted, or engine fails (fail-safe)."""
    if not audio_path:
        return []

    try:
        path = Path(audio_path)
        if not path.exists() or not path.is_file():
            return []

        # --- Attempt faster-whisper first (preferred: lower memory, CTranslate2) ---
        try:
            from faster_whisper import WhisperModel  # type: ignore

            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments_iter, _ = model.transcribe(str(path))
            results: List[TranscriptSegment] = []
            for idx, seg in enumerate(segments_iter):
                text = seg.text.strip()
                if not text:
                    continue
                results.append(
                    TranscriptSegment(
                        id=f"seg_{idx}",
                        start_time=max(0.0, float(seg.start)),
                        end_time=max(float(seg.start), float(seg.end)),
                        text=text,
                    )
                )
            return results

        except ImportError:
            pass  # fall through to openai-whisper

        # --- Attempt openai-whisper ---
        try:
            import whisper  # type: ignore

            model = whisper.load_model("base")
            result = model.transcribe(str(path))
            segments_raw = result.get("segments", [])
            results = []
            for idx, seg in enumerate(segments_raw):
                text = str(seg.get("text", "")).strip()
                if not text:
                    continue
                start = max(0.0, float(seg.get("start", 0.0)))
                end = max(start, float(seg.get("end", start)))
                results.append(
                    TranscriptSegment(
                        id=f"seg_{idx}",
                        start_time=start,
                        end_time=end,
                        text=text,
                    )
                )
            return results

        except ImportError:
            pass  # no speech engine available

        # Both engines absent — fail safely
        return []

    except Exception:
        return []


if __name__ == "__main__":
    # 1. Test None input
    assert transcribe_audio(None) == []
    # 2. Test non-existent file: must return empty list, not crash
    assert transcribe_audio("non_existent_audio.wav") == []
    # 3. Test empty string input
    assert transcribe_audio("") == []
    print("ALL SPEECH ACCEPTANCE TESTS PASSED")
