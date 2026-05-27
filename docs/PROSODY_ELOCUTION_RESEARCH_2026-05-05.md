# Prosody & Elocution Research Notes - 2026-05-05

## Sources Consulted

| Category | Source | URL | Relevance |
| --- | --- | --- | --- |
| HuBERT | HuBERT: Self-Supervised Speech Representation Learning by Masked Prediction of Hidden Units | https://huggingface.co/papers/2106.07447 | Establishes HuBERT as a pretrained self-supervised speech representation model. |
| HuBERT model | facebook/hubert-base-ls960 model card | https://huggingface.co/facebook/hubert-base-ls960 | Documents 16 kHz pretrained HuBERT base feature extraction model. |
| WavLM comparison | WavLM: Large-Scale Self-Supervised Pre-Training for Full Stack Speech Processing | https://www.microsoft.com/en-us/research/publication/wavlm-large-scale-self-supervised-pre-training-for-full-stack-speech-processing/ | Supports future comparison for speaker/paralinguistic/full-stack speech tasks. |
| Dubbing duration | Duration modeling of neural TTS for automatic dubbing | https://www.amazon.science/publications/duration-modeling-of-neural-tts-for-automatic-dubbing | Frames isochrony, pauses, and TTS duration control as practical dubbing constraints. |
| Prosodic alignment | Prosodic Alignment for off-screen automatic dubbing | https://arxiv.org/abs/2204.02530 | Supports phrase/pause alignment as part of audiovisual coherence. |
| Human dubbing practice | Dubbing in Practice: A Large Scale Study of Human Localization With Insights for Automatic Dubbing | https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00551/115968/Dubbing-in-Practice-A-Large-Scale-Study-of-Human | Shows timing, vocal naturalness, and source speech characteristics matter beyond text translation. |

Access date: 2026-05-06.

## Why Prosody Matters For Dubbing

Translation and TTS alone can produce intelligible speech, but dubbing also has timing and delivery constraints. Rhythm, pauses, speech rate, energy, emphasis, and duration pressure affect whether a dubbed line feels synchronized with the video and emotionally connected to the source performance.

## What HuBERT Offers

HuBERT provides pretrained self-supervised speech representations. In this phase Vidiolingua uses `facebook/hubert-base-ls960` as a frozen feature extractor for source and dubbed audio. These embeddings are useful for measurable source-vs-dub comparison, especially when combined with explicit timing and energy features.

## What HuBERT Does Not Solve

HuBERT does not by itself guarantee pitch transfer, emotion transfer, speaker cloning, or human-level dubbing. It is not a prosody transfer system. Vidiolingua does not train HuBERT from scratch.

## WavLM Note

WavLM is a strong future comparison candidate because it was proposed for broader downstream speech tasks including speaker and paralinguistic information. This phase implements HuBERT first because the requested feature is HuBERT-guided prosody and because HuBERT has a stable pretrained model card suitable for feature extraction.

## Implemented Now

- Source prosody profile: segment duration, pause pattern, speech rate, energy contour, intonation proxy, heuristic emphasis hints.
- Cross-lingual prosody guidance plan: duration pressure, pacing recommendation, pause guidance, punctuation strategy, backend controls.
- HuBERT feature worker: isolated `.venv_prosody` subprocess with `facebook/hubert-base-ls960`.
- Lightweight adapter: ridge/baseline calibration on frozen HuBERT embeddings and handcrafted prosody features.
- Validation reports: source-vs-dub prosody proxy and HuBERT-guided similarity.

## Limitations

- Pitch/F0 extraction is not implemented in the lightweight stdlib analyzer.
- Emotion/tone is heuristic only.
- HuBERT failure does not fail the main dubbing path.
- Adapter confidence is low with the current small project dataset.
- XTTS and Sarvam expose limited direct prosody controls, so Vidiolingua uses safe presets, chunking, pacing, and validation rather than claiming exact transfer.
