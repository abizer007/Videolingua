"""Voice utilities for VidioLingua.

Keep this package initializer lightweight. API/config tools import
`voice.base` for routing policy and should not load NumPy, torch, or Coqui XTTS
until the XTTS engine is actually used.
"""

__all__ = [
    "VoiceCloneConfig",
    "VoiceClonePreflightError",
    "VoiceClonePreflightResult",
    "VoiceCloneResult",
    "VoiceCloningError",
    "clone_voice",
    "preflight_xtts_voice_cloning",
]


def __getattr__(name: str):
    if name in __all__:
        from . import xtts_cloner

        return getattr(xtts_cloner, name)
    raise AttributeError(f"module 'voice' has no attribute {name!r}")
