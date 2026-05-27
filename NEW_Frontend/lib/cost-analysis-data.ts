export type EvidenceKind = "Measured" | "External source" | "Planning assumption" | "Requires update";

export type SourceBackedValue = {
  label: string;
  value: string;
  unit?: string;
  kind: EvidenceKind;
  source: string;
  url?: string;
  accessed: string;
  note: string;
  confidence: "High" | "Medium" | "Low";
};

export const accessDate = "2026-05-05";

export const measuredRunEvidence: SourceBackedValue[] = [
  {
    label: "French XTTS validated MP4",
    value: "30.574s, 78,499,361 bytes",
    kind: "Measured",
    source: "outputs/french_official_test/evaluation/metrics_report.json",
    accessed: accessDate,
    note: "Measured from the protected known-good French output. The route is XTTS with local runtime cost.",
    confidence: "High",
  },
  {
    label: "Kannada Sarvam validated MP4",
    value: "30.655s, 78,710,653 bytes",
    kind: "Measured",
    source: "outputs/kannada_sarvam_practical_test_clipfix/evaluation/metrics_report.json",
    accessed: accessDate,
    note: "Measured from the protected known-good Kannada output. The route is IndicTrans2 plus Sarvam managed Indian-language TTS.",
    confidence: "High",
  },
  {
    label: "French practical elapsed time",
    value: "305s",
    kind: "Measured",
    source: "outputs/french_official_test/pipeline_result.json",
    accessed: accessDate,
    note: "Historical local run timing. This is not a universal benchmark.",
    confidence: "High",
  },
  {
    label: "Kannada practical elapsed time",
    value: "166s",
    kind: "Measured",
    source: "outputs/kannada_sarvam_practical_test_clipfix/pipeline_result.json",
    accessed: accessDate,
    note: "Historical local run timing. This is not a universal benchmark.",
    confidence: "High",
  },
];

export const managedVoicePricing: SourceBackedValue[] = [
  {
    label: "Sarvam Bulbul v3 TTS",
    value: "INR 30 / 10K characters",
    kind: "External source",
    source: "Sarvam AI API pricing",
    url: "https://www.sarvam.ai/api-pricing",
    accessed: accessDate,
    note: "Current Kannada demo uses Sarvam for managed Indian-language speech, not exact voice cloning.",
    confidence: "High",
  },
  {
    label: "Sarvam Bulbul v2 TTS",
    value: "INR 15 / 10K characters",
    kind: "External source",
    source: "Sarvam API docs pricing",
    url: "https://docs.sarvam.ai/api-reference-docs/pricing",
    accessed: accessDate,
    note: "Provider pricing is character-billed and should be rechecked before final submission.",
    confidence: "High",
  },
  {
    label: "ElevenLabs Flash/Turbo TTS",
    value: "$0.05 / 1K characters",
    kind: "External source",
    source: "ElevenLabs API pricing",
    url: "https://elevenlabs.io/pricing/api",
    accessed: accessDate,
    note: "Comparison only; VideoLingua does not route the validated demo through ElevenLabs.",
    confidence: "High",
  },
  {
    label: "Google Cloud Chirp 3 HD",
    value: "$30 / 1M characters after free allowance",
    kind: "External source",
    source: "Google Cloud Text-to-Speech pricing",
    url: "https://cloud.google.com/text-to-speech/pricing",
    accessed: accessDate,
    note: "Comparison only; pricing varies by feature, region, and free usage terms.",
    confidence: "High",
  },
];

export const translationApiPricing: SourceBackedValue[] = [
  {
    label: "Google Cloud Translation NMT",
    value: "$20 / 1M characters after monthly credit",
    kind: "External source",
    source: "Google Cloud Translation pricing",
    url: "https://cloud.google.com/translate/pricing",
    accessed: accessDate,
    note: "Comparison route. VideoLingua currently uses local IndicTrans2 for the validated en->kn path.",
    confidence: "High",
  },
  {
    label: "Google Translation LLM",
    value: "$10 / 1M input + $10 / 1M output characters",
    kind: "External source",
    source: "Google Cloud Translation pricing",
    url: "https://cloud.google.com/translate/pricing",
    accessed: accessDate,
    note: "Comparison route for LLM translation economics, not measured VideoLingua runtime.",
    confidence: "High",
  },
  {
    label: "AWS Translate standard",
    value: "$15 / 1M characters",
    kind: "External source",
    source: "AWS Translate pricing",
    url: "https://aws.amazon.com/translate/pricing/",
    accessed: accessDate,
    note: "Comparison route; AWS free tier and document modes have separate terms.",
    confidence: "High",
  },
];

export const gpuPricing: SourceBackedValue[] = [
  {
    label: "RunPod RTX 4090",
    value: "from $0.59/hr secure, $0.34/hr community",
    kind: "External source",
    source: "RunPod RTX 4090 pricing",
    url: "https://www.runpod.io/gpu-models/rtx-4090",
    accessed: accessDate,
    note: "Useful for future self-hosted GPU workers. Throughput must be benchmarked on VideoLingua before cost claims.",
    confidence: "High",
  },
  {
    label: "Lambda 1x NVIDIA A10",
    value: "$0.75/GPU/hr",
    kind: "External source",
    source: "Lambda GPU Cloud pricing",
    url: "https://lambda.ai/service/gpu-cloud/pricing",
    accessed: accessDate,
    note: "Comparison for future GPU-hosted ASR/TTS/lip-sync workers.",
    confidence: "High",
  },
  {
    label: "Lambda 1x NVIDIA A100 PCIe",
    value: "$1.29/GPU/hr",
    kind: "External source",
    source: "Lambda GPU Cloud pricing",
    url: "https://lambda.ai/service/gpu-cloud/pricing",
    accessed: accessDate,
    note: "Comparison for heavier model routes; not a measured VideoLingua deployment cost.",
    confidence: "High",
  },
];

export const marketComparison: SourceBackedValue[] = [
  {
    label: "Rev global subtitles",
    value: "$6.49-$15.99 / video minute",
    kind: "External source",
    source: "Rev pricing",
    url: "https://support.rev.com/hc/en-us/articles/18893487380365-Pricing",
    accessed: accessDate,
    note: "Localization-market comparison for human subtitles, not full dubbing.",
    confidence: "High",
  },
  {
    label: "Voquent video/voice dubbing",
    value: "from $11 / minute",
    kind: "External source",
    source: "Voquent dubbing pricing",
    url: "https://www.voquent.com/dubbing/video/",
    accessed: accessDate,
    note: "Professional dubbing benchmark; quotes vary by scope, cast, language, mix, and minimum order.",
    confidence: "Medium",
  },
  {
    label: "Voquent dubbing packages",
    value: "$20-$62 / minute package starts",
    kind: "External source",
    source: "Voquent customer pricing guide",
    url: "https://www.voquent.com/pricing/",
    accessed: accessDate,
    note: "Market framing only, not a savings claim for VideoLingua.",
    confidence: "Medium",
  },
];

export const evaluationMetricDefinitions: SourceBackedValue[] = [
  {
    label: "WER",
    value: "(S + D + I) / N",
    kind: "External source",
    source: "Microsoft Learn speech evaluation",
    url: "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-custom-speech-evaluate-data",
    accessed: accessDate,
    note: "VideoLingua computes transcript reliability automatically; WER is shown only when a true transcript or independent ASR consensus exists.",
    confidence: "High",
  },
  {
    label: "BLEU",
    value: "Reference-based MT metric",
    kind: "External source",
    source: "Papineni et al., ACL 2002",
    url: "https://aclanthology.org/P02-1040/",
    accessed: accessDate,
    note: "Requires reference translation and should not be treated as a standalone quality truth.",
    confidence: "High",
  },
  {
    label: "chrF",
    value: "Character n-gram F-score",
    kind: "External source",
    source: "Popovic, WMT 2015",
    url: "https://aclanthology.org/W15-3049/",
    accessed: accessDate,
    note: "Requires reference translation. Useful for morphologically rich languages when properly configured.",
    confidence: "High",
  },
  {
    label: "MOS",
    value: "Mean opinion score terminology",
    kind: "External source",
    source: "ITU-T P.800.1 summary",
    url: "https://www.itu.int/dms_pubrec/itu-t/rec/p/T-REC-P.800.1-201607-I!!SUM-HTM-E.htm",
    accessed: accessDate,
    note: "VideoLingua computes an audio naturalness proxy automatically; human MOS is shown only when supplied by an expert.",
    confidence: "High",
  },
  {
    label: "LSE-C / LSE-D",
    value: "Lip-sync confidence and distance concepts",
    kind: "External source",
    source: "Wav2Lip / SyncNet-style evaluation literature",
    url: "https://www.mdpi.com/2079-9292/13/18/3657",
    accessed: accessDate,
    note: "VideoLingua computes an A/V sync proxy automatically; LSE-C/LSE-D are shown only when a true evaluator is installed.",
    confidence: "Medium",
  },
];
