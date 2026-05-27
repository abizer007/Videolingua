# Duration And Speed Diagnostics - 2026-04-28

This task added diagnostics only. It did not rewrite lipsync, install Wav2Lip or MuseTalk, or change the video muxing strategy.

## What Was Added

`tts/run_tts.py` now reports:

- Raw generated TTS duration per segment.
- Target segment duration.
- Atempo stretch ratio.
- Warnings when a segment requires notable speedup or slowdown.
- Final generated TTS duration.
- Difference between final TTS duration and translated source timeline.
- Whether per-segment atempo was applied.

`lipsync/run_lipsync.py` now reports:

- Original video duration.
- Generated audio duration.
- Audio/video duration difference before muxing.
- Whether ffmpeg `-shortest` is used.
- Whether lip-sync muxing itself applies speedup.
- Final MP4 duration.
- Final MP4/video duration difference.

`backend/pipeline_runner.py` now reports:

- Original video duration after TTS.
- Generated TTS WAV duration for each output.
- Difference between generated TTS and original video duration.
- Final MP4 duration after lipsync.
- Difference between final MP4 and original video duration.

## Current Behavior

The TTS stage uses per-segment ffmpeg `atempo` stretching to fit generated speech into each translated segment's original timestamp range. This can make speech feel fast if XTTS generates a segment much longer than the available source segment duration.

The ffmpeg lipsync fallback does not speed up audio. It muxes video and audio with `-shortest`, so a large duration mismatch can truncate whichever stream runs longer.

## Warning Thresholds

- TTS segment speedup warning: generated duration / target duration greater than 1.35.
- TTS segment slowdown warning: generated duration / target duration less than 0.75.
- Final TTS timeline warning: absolute mismatch greater than 0.50 seconds.
- Pipeline/lipsync duration warning: absolute audio/video mismatch greater than 1.00 second.

## Validation Run

The requested single French practical regression writes its logs to:

`outputs/french_quality_ab_hybrid_test/logs/`

The most relevant files are:

- `outputs/french_quality_ab_hybrid_test/logs/tts.stdout.log`
- `outputs/french_quality_ab_hybrid_test/logs/lipsync.stdout.log`

These logs should be used to identify any segment that is being compressed too aggressively.
