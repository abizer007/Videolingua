export type PipelineStage =
  | "uploading"
  | "bgm_separation"
  | "asr"
  | "translation"
  | "tts"
  | "lipsync"
  | "complete"
  | "failed"
  | "cancelled"
  | "timeout"
  | "error";

export type JobLifecycleStatus = "queued" | "running" | "complete" | "failed" | "cancelled" | "timeout" | "error" | string;

export type JobStatus = {
  schemaVersion?: string;
  jobId: string;
  status?: JobLifecycleStatus;
  terminal?: boolean;
  stage: PipelineStage;
  progress: number;
  currentLanguage?: string | null;
  languages?: string[];
  sourceLanguage?: string | null;
  sourceLanguageConfidence?: number | null;
  error?: string | null;
  metrics?: Record<string, number | string | boolean | null | undefined>;
  analysis?: RunAnalysis;
  metricsReport?: MetricsReport | null;
  startedAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  terminalAt?: string | null;
  completedAt?: string | null;
  failedAt?: string | null;
  cancelledAt?: string | null;
  timeoutAt?: string | null;
  elapsedSeconds?: number | null;
  errorSummary?: string | null;
  errorTracePath?: string | null;
  resultPath?: string | null;
  resultAvailable?: boolean;
  stageHistory?: Array<{
    stage: PipelineStage;
    startedAt?: string | null;
    completedAt?: string | null;
    durationSeconds?: number | null;
  }>;
  translationQA?: TranslationQASummary | null;
  linguisticIntegrity?: LinguisticIntegritySummary | null;
  phoneticResolution?: PhoneticResolutionSummary | null;
  prosodyElocution?: Record<string, number | string | boolean | null | undefined>;
  responsibleAI?: ResponsibleAISummary | null;
  captionsRequested?: boolean;
  manifestSummary?: JobManifestSummary | null;
  manifestPath?: string | null;
};

export type TranslationQASummary = {
  status?: "passed" | "warning" | "failed" | string | null;
  checksPassed?: number | null;
  warningsCount?: number | null;
  errorsCount?: number | null;
  emptySegments?: number | null;
  scriptMatch?: boolean | null;
  numberIssues?: number | null;
  entityIssues?: number | null;
  expansionRatioWarnings?: number | null;
  glossaryApplied?: boolean | null;
  translationMemoryHits?: number | null;
  postEditUsed?: boolean | null;
  postEditEngine?: string | null;
  reportPath?: string | null;
};

export type LinguisticIntegritySummary = {
  status?: "passed" | "warning" | "failed" | string | null;
  score?: number | null;
  severity?: string | null;
  scriptStatus?: string | null;
  emptySegments?: number | null;
  numberWarnings?: number | null;
  nameWarnings?: number | null;
  expansionWarnings?: number | null;
  reportPath?: string | null;
};

export type PhoneticResolutionSummary = {
  status?: "passed" | "warning" | "failed" | string | null;
  phoneticRiskScore?: number | null;
  termsDetected?: number | null;
  acronymsDetected?: number | null;
  ambiguityWarnings?: number | null;
  dictionaryUsed?: boolean | null;
  reportPath?: string | null;
};

export type ManifestStageStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export type JobManifestSummary = {
  job_id?: string | null;
  final_status?: "pending" | "running" | "completed" | "failed" | string | null;
  current_stage?: string | null;
  last_completed_stage?: string | null;
  failed_stage?: string | null;
  stage_statuses?: Record<string, {
    status?: ManifestStageStatus | string | null;
    attempt_count?: number | null;
    elapsed_sec?: number | null;
    can_retry?: boolean | null;
    can_resume_from_here?: boolean | null;
    error_message?: string | null;
  }>;
  selected_backends?: {
    translation?: string | null;
    voice?: string | null;
  };
  routing?: Record<string, number | string | boolean | null | undefined>;
  important_artifacts?: Record<string, {
    name?: string | null;
    stage?: string | null;
    kind?: string | null;
    exists?: boolean | null;
    sizeBytes?: number | null;
  } | Array<{
    name?: string | null;
    stage?: string | null;
    kind?: string | null;
    exists?: boolean | null;
    sizeBytes?: number | null;
  }> | null>;
  user_facing_error?: string | null;
  manifest_path?: string | null;
  resume_supported?: boolean | null;
  resume_command_hint?: string | null;
  retry_failed_stage_hint?: string | null;
};

export type RunAnalysis = {
  run_evidence?: Record<string, number | string | boolean | null | undefined>;
  translationQA?: TranslationQASummary | null;
  linguisticIntegrity?: LinguisticIntegritySummary | null;
  phoneticResolution?: PhoneticResolutionSummary | null;
  speaker_analysis?: {
    status?: "pending" | "not_run" | "computed" | "failed" | "unavailable" | "not_determined" | string;
    speakers_detected?: number | null;
    speaker_count?: number | null;
    source?: string | null;
    reason?: string | null;
    recommended_fix?: string | null;
    segment_count?: number | null;
    unknown_segment_count?: number | null;
    ambiguous_segment_count?: number | null;
    speaker_labels?: string[];
    speaker_reference_count?: number | null;
    voice_assignment_status?: string | null;
    visual_analysis_status?: string | null;
    sarvam_voice_plan_speakers?: Array<{
      speaker_id?: string | null;
      voice_profile_hint?: string | null;
      confidence?: string | null;
      hint_source?: string | null;
      selected_tts_voice?: string | null;
      selection_reason?: string | null;
    }>;
    warnings?: string[];
    errors?: string[];
  };
  reference_audio?: Record<string, number | string | boolean | null | undefined>;
  output_inspection?: Record<string, number | string | boolean | null | undefined>;
  source_captions?: Record<string, number | string | boolean | null | undefined | string[]>;
  lipsync?: Record<string, number | string | boolean | null | undefined | string[]>;
  audio_validation?: Record<string, number | string | boolean | null | undefined>;
  advanced_metrics?: Record<string, { status?: string }>;
  prosodyElocution?: Record<string, number | string | boolean | null | undefined>;
};

export type MetricResult = {
  status?: string;
  value?: number | string | boolean | null;
  unit?: string;
  label?: string;
  method?: string;
  confidence?: string;
  explanation?: string;
  reference_type?: string;
  reason?: string | null;
  source?: string | null;
  notes?: string | null;
  details?: Record<string, number | string | boolean | null | undefined | Record<string, unknown>>;
};

export type EvaluationSection = {
  display_label?: string;
  score?: MetricResult;
  asr_accuracy?: MetricResult;
  wer?: MetricResult;
  cer?: MetricResult;
  bleu?: MetricResult;
  chrf?: MetricResult;
  mos?: MetricResult;
  naturalness_score?: MetricResult;
  lse_c?: MetricResult;
  lse_d?: MetricResult;
  voice_similarity?: MetricResult;
  signals?: Record<string, number | string | boolean | null | undefined | string[]>;
  [key: string]: unknown;
};

export type MetricsReport = {
  schema_version?: number;
  evaluation_mode?: string;
  generated_at?: string;
  metric_sources?: Record<string, string>;
  asr?: EvaluationSection;
  translation?: EvaluationSection;
  voice?: EvaluationSection;
  sync?: EvaluationSection;
  speaker?: EvaluationSection;
  overall?: {
    overall_quality_index?: MetricResult;
    score_0_100?: number;
    grade?: string;
    confidence?: string;
    components?: Record<string, Record<string, number | string | boolean | null | undefined>>;
    excluded_components?: Record<string, string>;
    explanation?: string;
  };
  output_validation?: EvaluationSection;
  operational?: Record<string, number | string | boolean | null | undefined | Record<string, number>>;
  transcript?: Record<string, number | string | boolean | null | undefined | string[]>;
  voice_audio?: Record<string, number | string | boolean | null | undefined>;
  prosody?: Record<string, number | string | boolean | null | undefined>;
  responsible_ai?: Record<string, number | string | boolean | null | undefined | string[]>;
  media_output?: Record<string, number | string | boolean | null | undefined>;
  lipsync?: Record<string, number | string | boolean | null | undefined | string[]>;
  reference_audio?: Record<string, number | string | boolean | null | undefined>;
  validation?: Record<string, number | string | boolean | null | undefined | string[]>;
  optional_reference_metrics?: Record<string, MetricResult>;
  warnings?: string[];
  errors?: string[];
  audio?: Record<string, number | string | boolean | null | undefined>;
  media?: Record<string, number | string | boolean | null | undefined>;
  advanced?: Record<string, MetricResult>;
  inputs?: Record<string, boolean>;
};

export type ProcessingResult = {
  jobId: string;
  status?: JobLifecycleStatus;
  terminal?: boolean;
  stage?: string;
  originalVideo: string;
  localizedVideos: Array<{
    language: string;
    url: string;
    confidence?: number;
    captions?: CaptionTrack[];
  }>;
  captionsRequested?: boolean;
  captions?: CaptionTrack[];
  metrics: {
    totalTime: number;
    languagesProcessed: number;
    bgmPreserved?: boolean;
    speakersDetected?: number | null;
  } & Record<string, number | string | boolean | null | undefined>;
  analysis?: RunAnalysis;
  metricsReport?: MetricsReport;
  translationQA?: TranslationQASummary | null;
  linguisticIntegrity?: LinguisticIntegritySummary | null;
  phoneticResolution?: PhoneticResolutionSummary | null;
  responsibleAI?: ResponsibleAISummary | null;
  manifestSummary?: JobManifestSummary | null;
  manifestPath?: string | null;
  error?: string;
  errorSummary?: string;
};

export type CaptionTrack = {
  kind?: "subtitles" | "captions" | string;
  format?: "vtt" | "srt" | string;
  languageCode?: string | null;
  label?: string | null;
  source?: "asr_original" | string | null;
  url: string;
  cueCount?: number | null;
};

export type ResponsibleAISummary = {
  enabled?: boolean;
  mode?: "report_only" | "strict" | string | null;
  passportStatus?: string | null;
  sgiRiskLevel?: "low" | "medium" | "high" | string | null;
  syntheticVoiceUsed?: boolean | null;
  speakerConsentRecorded?: boolean | null;
  visibleDisclosureApplied?: boolean | null;
  audioDisclosureApplied?: boolean | null;
  provenanceManifestCreated?: boolean | null;
  hashesGenerated?: boolean | null;
  auditLedgerCreated?: boolean | null;
  safeForDemoExport?: boolean | null;
  warningsCount?: number | null;
  errorsCount?: number | null;
  passportPath?: string | null;
  provenancePath?: string | null;
  message?: string | null;
};

export type UploadPayload = {
  video: File;
  targetLanguage: string;
  sourceLanguage?: string;
  voiceSample?: File | null;
  autoReference?: boolean;
  referenceMode?: "uploaded" | "auto_extract" | "none";
  groundTruthTranscriptFile?: File | null;
  groundTruthTranscriptText?: string;
  referenceTranslationFile?: File | null;
  referenceTranslationText?: string;
  humanMosRating?: string;
  humanQualityNotes?: string;
  includeCaptions?: boolean;
  cloningRequired: boolean;
  responsibleAIConsent?: {
    contentOwnerConfirmation?: boolean;
    speakerConsent?: boolean;
    intendedUse?: string;
    commercialUseAllowed?: boolean;
    retentionDays?: number;
  };
};

export type StoredJob = {
  storageVersion?: number;
  jobId: string;
  runSessionId?: string;
  targetLanguage: string;
  voiceBackend: string;
  voiceLabel: string;
  translationBackend: string;
  videoName: string;
  sourceFileName?: string;
  voiceSampleName?: string;
  referenceMode?: "uploaded" | "auto_extract" | "none";
  includeCaptions?: boolean;
  createdAt: string;
  updatedAt?: string;
  status?: JobLifecycleStatus;
  terminal?: boolean;
};

export type MultilingualExportLanguage = {
  language: string;
  display_name: string;
  audio_track_path: string;
  source_audio_path?: string | null;
  source_result_folder?: string | null;
  translation_backend?: string | null;
  voice_backend?: string | null;
  voice_mode?: string | null;
  is_exact_clone?: boolean | null;
  validation_status?: string | null;
  duration_sec?: number | null;
  sample_rate?: number | null;
  channels?: number | null;
  codec?: string | null;
};

export type MultilingualExportManifest = {
  schema_version?: number;
  export_id: string;
  created_at?: string;
  source_video?: {
    path?: string | null;
    original_path?: string | null;
    duration_sec?: number | null;
    hash?: string | null;
    codec?: string | null;
    width?: number | null;
    height?: number | null;
    avg_frame_rate?: string | null;
  };
  languages: MultilingualExportLanguage[];
  exports?: {
    hls_master?: string | null;
    multi_audio_mp4?: string | null;
  };
  warnings?: string[];
  errors?: string[];
};

export type MultilingualExportResponse = {
  exportId: string;
  status?: string;
  manifest: MultilingualExportManifest;
  links?: {
    manifest?: string | null;
    validationReport?: string | null;
    hlsMaster?: string | null;
    multiAudioMp4?: string | null;
  };
};
