from __future__ import annotations

import os
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import numpy as np

from voice.audio_validation import file_sha256, read_audio_mono, validate_generated_audio
from voice.xtts_cloner import (
    VoiceCloneConfig,
    VoiceCloningError,
    build_voice_cache_key,
    clone_voice,
    preflight_xtts_voice_cloning,
    resolve_xtts_model_files,
)


def _write_test_wav(path: Path, duration_s: float = 6.5, freq: float = 220.0, sr: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(duration_s * sr), dtype=np.float32) / sr
    samples = 0.18 * np.sin(2 * np.pi * freq * t)
    pcm = (samples * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


class FakeXTTS:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def tts_to_file(self, **kwargs) -> None:
        self.calls.append(kwargs)
        if not kwargs.get("speaker_wav"):
            raise AssertionError("speaker_wav was not passed")
        text = kwargs["text"]
        duration = max(0.35, min(1.2, len(text.split()) * 0.12))
        _write_test_wav(Path(kwargs["file_path"]), duration_s=duration, freq=330.0)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class XTTSVoiceCloningTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp_root = Path.cwd() / ".runtime_tmp" / "xtts_tests"
        tmp_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=tmp_root)
        self.root = Path(self.tmp.name)
        self.reference = self.root / "reference.wav"
        _write_test_wav(self.reference)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _config(self) -> VoiceCloneConfig:
        return VoiceCloneConfig(
            intermediate_dir=self.root / "outputs" / "intermediate",
            voice_cloning_required=True,
            allow_generic_tts_fallback=False,
        )

    def _mock_preflight(self):
        return mock.patch("voice.xtts_cloner.preflight_xtts_voice_cloning")

    def test_missing_reference_audio_fails(self) -> None:
        with self.assertRaises(VoiceCloningError):
            clone_voice("hello", str(self.root / "missing.wav"), self.root / "out.wav", config=self._config())

    def test_empty_reference_audio_fails(self) -> None:
        empty = self.root / "empty.wav"
        empty.write_bytes(b"")
        with self.assertRaises(VoiceCloningError):
            clone_voice("hello", str(empty), self.root / "out.wav", config=self._config())

    def test_xtts_call_receives_speaker_wav_and_language(self) -> None:
        fake = FakeXTTS()
        with self._mock_preflight(), mock.patch("voice.xtts_cloner._load_xtts_model", return_value=fake):
            result = clone_voice(
                "This is a short cloned voice test.",
                str(self.reference),
                self.root / "out.wav",
                language="en",
                config=self._config(),
            )
        self.assertTrue(result.speaker_wav_used)
        self.assertFalse(result.fallback_attempted)
        self.assertTrue(fake.calls)
        self.assertEqual(fake.calls[0]["language"], "en")
        self.assertTrue(fake.calls[0]["speaker_wav"].endswith("reference_clean.wav"))

    def test_generated_output_is_wav_and_decodable(self) -> None:
        with self._mock_preflight(), mock.patch("voice.xtts_cloner._load_xtts_model", return_value=FakeXTTS()):
            result = clone_voice(
                "This is a short cloned voice test.",
                str(self.reference),
                self.root / "out.wav",
                language="en",
                config=self._config(),
            )
        stats = validate_generated_audio(result.output_path)
        self.assertGreater(stats.duration_s, 0.2)
        self.assertEqual(Path(result.output_path).suffix.lower(), ".wav")

    def test_chunked_generation_joins_without_large_click(self) -> None:
        long_text = (
            "This is the first sentence in a longer cloned voice test. "
            "This is the second sentence and it should become another chunk. "
            "This is the third sentence to make sure joining is exercised."
        )
        config = self._config()
        config.max_chars = 70
        with self._mock_preflight(), mock.patch("voice.xtts_cloner._load_xtts_model", return_value=FakeXTTS()):
            result = clone_voice(long_text, str(self.reference), self.root / "out.wav", "en", config)
        samples, _ = read_audio_mono(Path(result.output_path))
        self.assertEqual(result.chunks, 3)
        self.assertLess(float(np.max(np.abs(np.diff(samples)))), 0.30)

    def test_cache_key_changes_when_reference_changes(self) -> None:
        ref2 = self.root / "reference2.wav"
        _write_test_wav(ref2, freq=440.0)
        key1 = build_voice_cache_key(
            text="same text",
            reference_audio_path=self.reference,
            model_name="tts_models/multilingual/multi-dataset/xtts_v2",
            language="en",
        )
        key2 = build_voice_cache_key(
            text="same text",
            reference_audio_path=ref2,
            model_name="tts_models/multilingual/multi-dataset/xtts_v2",
            language="en",
        )
        self.assertNotEqual(key1, key2)
        self.assertNotEqual(file_sha256(self.reference), file_sha256(ref2))

    def test_wrong_model_fails_clearly(self) -> None:
        config = self._config()
        config.model_name = "tts_models/en/ljspeech/tacotron2-DDC"
        with self.assertRaisesRegex(VoiceCloningError, "Wrong XTTS model"):
            clone_voice("hello there", str(self.reference), self.root / "out.wav", "en", config)

    def test_unsupported_language_fails(self) -> None:
        with self.assertRaisesRegex(VoiceCloningError, "does not support language"):
            clone_voice("hello there", str(self.reference), self.root / "out.wav", "hi", self._config())

    def test_reference_prep_preserves_duration(self) -> None:
        from voice.reference_audio import prepare_reference_audio

        cleaned, stats = prepare_reference_audio(
            self.reference,
            intermediate_dir=self.root / "prep",
        )
        self.assertTrue(cleaned.is_file())
        self.assertGreaterEqual(stats.duration_s, 6.0)
        self.assertLess(abs(stats.duration_s - 6.5), 0.15)
        self.assertEqual(stats.sample_rate, 24000)

    def test_model_file_resolution_requires_local_files(self) -> None:
        model_dir = self.root / "xtts_v2"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        (model_dir / "model.pth").write_bytes(b"weights")
        (model_dir / "vocab.json").write_text("{}", encoding="utf-8")
        config = self._config()
        config.model_path = model_dir
        files = resolve_xtts_model_files(config)
        self.assertEqual(Path(files.model_dir), model_dir)
        self.assertTrue(files.config_path.endswith("config.json"))


class TTSFallbackPolicyTests(unittest.TestCase):
    def test_generic_fallback_is_blocked_when_cloning_required(self) -> None:
        import tts.run_tts as run_tts

        with mock.patch.dict(
            os.environ,
            {
                "VOICE_CLONING_REQUIRED": "true",
                "ALLOW_GENERIC_TTS_FALLBACK": "false",
                "VIDIOLINGUA_TTS_ENGINE": "xtts",
                "VIDIOLINGUA_VOICE_SAMPLE": __file__,
            },
            clear=False,
        ):
            with mock.patch.object(run_tts, "_synthesize_xtts", side_effect=RuntimeError("boom")):
                with mock.patch.object(run_tts, "_synthesize_legacy") as legacy:
                    with self.assertRaises(RuntimeError):
                        run_tts.synthesize_segment(
                            "hello",
                            "en",
                            Path(tempfile.gettempdir()) / "blocked_fallback.wav",
                            voice_options={"cloned": True},
                            speaker_wav=__file__,
                        )
                    legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
