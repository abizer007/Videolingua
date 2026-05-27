# Managed Indian Voice Backends - 2026-04-29

Decision: use Sarvam AI as the practical Indian-language voice backend.

Sarvam routing:

```text
hi -> hi-IN
ta -> ta-IN
bn -> bn-IN
te -> te-IN
kn -> kn-IN
ml -> ml-IN
mr -> mr-IN
gu -> gu-IN
pa -> pa-IN
or/od -> od-IN
```

Sarvam also supports `en-IN`, but VidioLingua does not route English to Sarvam
by default because XTTS already supports English.

XTTS remains primary for:

```text
ar, cs, de, en, es, fr, hu, it, ja, ko, nl, pl, pt, ru, tr, zh
```

IndicF5 remains present as disabled/local-experimental scaffolding. It is not
the practical default because native Windows local load-only validation timed
out and created memory risk.

Policy notes:

- Sarvam is managed TTS, not exact speaker cloning.
- Generic fallback remains blocked when `cloning_required=true`.
- Indic Parler is forbidden.
- API keys belong only in gitignored env files.
