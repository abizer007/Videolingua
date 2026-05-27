# Deep Technical Architecture Frontend Report - 2026-05-06

## Summary

Added a deep technical architecture section to the existing frontend
Architecture page without replacing the existing content.

Updated:

```text
NEW_Frontend\app\architecture\page.tsx
```

Created supporting research and diagram source files:

```text
docs\DEEP_TECHNICAL_ARCHITECTURE_RESEARCH_2026-05-06.md
docs\RUNTIME_ENVIRONMENT_MATRIX_2026-05-06.md
docs\architecture\package_diagram.mmd
docs\architecture\component_diagram.mmd
docs\architecture\deployment_diagram.mmd
docs\architecture\sequence_pipeline_run.mmd
docs\architecture\sequence_indictrans2_worker.mmd
docs\architecture\sequence_voice_backend_selection.mmd
docs\architecture\artifact_flow_diagram.mmd
```

## Frontend Placement

The new section is appended below the existing architecture content and before
`AnimatedPipelineCodeSection`.

Preserved existing page content:

- hero copy
- `InteractiveArchitectureDiagram`
- `ArchitectureFlow`
- OTT-style multilingual delivery section
- existing architecture lane cards
- existing "A route you can inspect" CTA
- animated pipeline code section
- site navigation and footer

## New Section Contents

The frontend now shows:

- runtime isolation overview for `.venv_api`, `.venv_tts`,
  `.venv_indictrans2`, `.venv_indicf5`, and `.venv_prosody`
- verified package versions and runtime status
- package/component/deployment map as a styled static UI
- repository paths for Mermaid diagram sources
- worker-call architecture and request/response JSON pattern
- current pipeline call chain from frontend upload to result polling
- artifact flow table for manifests, ASR JSON, translation reports, TTS WAV,
  final MP4, metrics, compliance, and multilingual export manifests
- engineering decisions table tied to verified source docs/reports
- verified / inferred / needs-verification boundary cards
- "what this enables" summary

## Design Approach

No new frontend dependency was added. Mermaid source files live under
`docs\architecture`, while the page renders a custom static diagram/table/card
layout that matches the current Vidiolingua visual system:

- white background / card surfaces
- thin borders
- large display typography
- compact evidence tables
- lucide icons already available in the project
- no raw JSON dump
- no secrets or env values

## Evidence Boundary

Displayed facts are based on:

- source code inspection
- docs and command logs
- safe `importlib.metadata` package-version probes
- safe torch CUDA availability probes
- env-file key-presence checks that did not print values

The page explicitly labels:

- verified facts
- inferred process/memory architecture
- items needing verification

## Safety Confirmation

- No backend runtime logic changed.
- No routing behavior changed.
- No venvs were mutated.
- No dependencies were installed.
- No full video pipeline was run.
- No local IndicF5 load was run.
- No Sarvam key or token value was exposed.
- Existing Architecture page content was preserved.
- Protected outputs and `models\xtts_v2` were not touched.

## Validation

Frontend:

```text
corepack pnpm run lint
passed after Corepack cache escalation

corepack pnpm run build
passed; /architecture generated successfully
```

The build emitted the existing `baseline-browser-mapping` age warning and
skipped type validation per the current project config.

Backend compile was not run because this pass did not change backend Python
runtime logic.
