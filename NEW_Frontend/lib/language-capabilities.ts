export type VoiceFamily = "xtts" | "sarvam" | "indicf5-disabled";

export type LanguageCapability = {
  code: string;
  name: string;
  family: VoiceFamily;
  voiceLabel: string;
  translationBackend: string;
  referenceAudio: "required" | "optional" | "disabled";
  accentClass: string;
  description: string;
};

const xttsDescription = "Uses a required reference audio file for speaker-style dubbing on the XTTS route.";
const sarvamDescription = "Routes to Sarvam for managed regional-language speech. Not exact speaker cloning.";

export const xttsLanguages: LanguageCapability[] = [
  { code: "ar", name: "Arabic", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "cs", name: "Czech", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "de", name: "German", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "en", name: "English", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "es", name: "Spanish", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "fr", name: "French", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Legacy compatible translation path", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "hu", name: "Hungarian", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "it", name: "Italian", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "ja", name: "Japanese", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "ko", name: "Korean", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "nl", name: "Dutch", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "pl", name: "Polish", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "pt", name: "Portuguese", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "ru", name: "Russian", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "tr", name: "Turkish", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
  { code: "zh", name: "Chinese", family: "xtts", voiceLabel: "XTTS speaker-reference voice", translationBackend: "Translation router", referenceAudio: "required", accentClass: "from-cyan-500 to-blue-500", description: xttsDescription },
];

export const sarvamLanguages: LanguageCapability[] = [
  { code: "hi", name: "Hindi", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "ta", name: "Tamil", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "bn", name: "Bengali", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "te", name: "Telugu", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "kn", name: "Kannada", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 for en -> kn", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "ml", name: "Malayalam", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "mr", name: "Marathi", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "gu", name: "Gujarati", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "pa", name: "Punjabi", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "or", name: "Odia", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: sarvamDescription },
  { code: "od", name: "Odia alias", family: "sarvam", voiceLabel: "Sarvam managed Indian-language voice", translationBackend: "IndicTrans2 when supported", referenceAudio: "optional", accentClass: "from-emerald-500 to-green-500", description: "Alias accepted by the backend when configured. Not exact speaker cloning." },
];

export const allLanguages = [...xttsLanguages, ...sarvamLanguages];

export function getLanguageCapability(code: string) {
  return allLanguages.find((language) => language.code === code) ?? allLanguages.find((language) => language.code === "fr")!;
}

export function backendNameForLanguage(code: string) {
  const capability = getLanguageCapability(code);
  if (capability.family === "sarvam") return "Sarvam";
  if (capability.family === "xtts") return "XTTS";
  return "IndicF5 disabled";
}
