# Final Routing Audit - 2026-04-29

## Config Inspect

`tools.inspect_pipeline_config` passed.

Confirmed:

- Sarvam enabled with masked key.
- Indic voice backend is `sarvam`.
- IndicF5 is `false` / `local_disabled`.
- XTTS model directory is ready.
- IndicTrans2 worker path exists.
- Indic Parler status is `disabled_absent_forbidden`.

Sarvam regional languages:

```text
hi, ta, bn, te, kn, ml, mr, gu, pa, or/od
```

XTTS languages:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh
```

## Voice Router Dry-Runs

Kannada:

```text
selected_engine=sarvam
xtts_used=false
indicf5_used=false
generic_fallback_used=false
indic_parler_used=false
managed_tts=true
exact_voice_clone=false
```

Hindi:

```text
selected_engine=sarvam
xtts_used=false
indicf5_used=false
generic_fallback_used=false
indic_parler_used=false
managed_tts=true
exact_voice_clone=false
```

French:

```text
selected_engine=xtts
sarvam_used=false
indicf5_used=false
generic_fallback_used=false
```

## Translation Router

EN -> KN validation passed:

```text
selected_engine=indictrans2
used_indictrans2=true
used_llm=false
used_deep_translator=false
fallback_used=false
```

Kannada output was present.

## Audit Result

Routing is correct for the current backend state:

- `kn -> Sarvam`
- `hi -> Sarvam`
- `fr -> XTTS`
- `en -> kn translation -> IndicTrans2`

Generic fallback remains blocked for cloned/strict practical routing.
