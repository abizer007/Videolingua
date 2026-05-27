# Final Output Artifact Audit - 2026-04-29

## Required Artifacts

French known-good:

| Path | Size |
| --- | ---: |
| `outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4` | 78,499,361 bytes |
| `outputs\french_official_test\pipeline_result.json` | 482 bytes |

Kannada known-good:

| Path | Size |
| --- | ---: |
| `outputs\kannada_sarvam_practical_test_clipfix\results\Vidiolingua_Test_Official_dubbed_kn.mp4` | 78,710,653 bytes |
| `outputs\kannada_sarvam_practical_test_clipfix\tts\output\Vidiolingua_Test_Official_transcription_kn.wav` | 1,351,964 bytes |
| `outputs\kannada_sarvam_practical_test_clipfix\translation\output\Vidiolingua_Test_Official_transcription_kn.json` | 1,913 bytes |
| `outputs\kannada_sarvam_practical_test_clipfix\pipeline_result.json` | 529 bytes |

All required artifacts exist and are non-empty.

## ffprobe: French MP4

Path:

```text
outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

Summary:

```text
duration=30.573991s
size=78,499,361 bytes
video_exists=true
video_codec=h264
resolution=1920x1080
fps=30
audio_exists=true
audio_codec=aac
audio_sample_rate=44100
audio_channels=2
```

## ffprobe: Kannada MP4

Path:

```text
outputs\kannada_sarvam_practical_test_clipfix\results\Vidiolingua_Test_Official_dubbed_kn.mp4
```

Summary:

```text
duration=30.655011s
size=78,710,653 bytes
video_exists=true
video_codec=h264
resolution=1920x1080
fps=30
audio_exists=true
audio_codec=aac
audio_sample_rate=44100
audio_channels=2
```

## Audit Result

French XTTS and Kannada Sarvam proof outputs are available for frontend result
display/download testing.
