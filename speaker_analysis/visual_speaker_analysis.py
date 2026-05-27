"""Practical visual speaker/person presence analysis.

With only OpenCV Haar cascades available, this reports face presence only.
It does not classify identity, presentation, or voice profile.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def analyze_visual_speakers(video_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    try:
        import cv2
    except Exception:
        report = {
            "status": "unavailable_without_model",
            "method": "opencv_unavailable",
            "faces_detected": None,
            "visible_person_hint": "unknown",
            "voice_profile_hint": "unknown",
            "confidence": "low",
            "warnings": [
                "OpenCV is not installed in this runtime. Visual analysis was not run.",
                "No visual voice-profile inference was attempted.",
            ],
            "errors": [],
        }
        return _write_if_requested(report, output_path)

    video_path = Path(video_path)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if not cascade_path.is_file():
        report = {
            "status": "unavailable_without_model",
            "method": "haar_cascade_missing",
            "faces_detected": None,
            "visible_person_hint": "unknown",
            "voice_profile_hint": "unknown",
            "confidence": "low",
            "warnings": ["OpenCV is available but the Haar face cascade is missing."],
            "errors": [],
        }
        return _write_if_requested(report, output_path)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        report = {
            "status": "failed",
            "method": "opencv_haar_face_presence",
            "faces_detected": None,
            "visible_person_hint": "unknown",
            "voice_profile_hint": "unknown",
            "confidence": "low",
            "warnings": [],
            "errors": [f"OpenCV could not open video: {video_path}"],
        }
        return _write_if_requested(report, output_path)

    face_cascade = cv2.CascadeClassifier(str(cascade_path))
    frames_sampled = 0
    frames_with_faces = 0
    max_faces = 0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, frame_count // 24) if frame_count else 60
    index = 0
    while frames_sampled < 24:
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        count = len(faces)
        if count:
            frames_with_faces += 1
            max_faces = max(max_faces, count)
        frames_sampled += 1
        index += step
    cap.release()

    report = {
        "status": "face_presence_detected" if frames_with_faces else "computed",
        "method": "opencv_haar_face_presence",
        "frames_sampled": frames_sampled,
        "frames_with_faces": frames_with_faces,
        "faces_detected": max_faces,
        "visible_person_hint": "visible_faces" if frames_with_faces else "unknown",
        "voice_profile_hint": "unknown",
        "confidence": "low",
        "warnings": [
            "OpenCV Haar analysis reports face presence only.",
            "No identity, presentation, or voice-profile classification was attempted.",
        ],
        "errors": [],
    }
    return _write_if_requested(report, output_path)


def _write_if_requested(report: dict[str, Any], output_path: str | Path | None) -> dict[str, Any]:
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
