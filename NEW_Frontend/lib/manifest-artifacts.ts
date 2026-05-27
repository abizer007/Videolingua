import type { JobManifestSummary, ProcessingResult } from "@/lib/types";

type ArtifactEntry = {
  name?: string | null;
  stage?: string | null;
  kind?: string | null;
  exists?: boolean | null;
  sizeBytes?: number | null;
};

export type ManifestArtifactRow = {
  key: string;
  label: string;
  value: string;
  meta: string;
};

function artifactEntries(value: ArtifactEntry | ArtifactEntry[] | null | undefined) {
  if (Array.isArray(value)) return value.filter(Boolean);
  return value ? [value] : [];
}

function artifactKey(group: string, entry: ArtifactEntry) {
  return [group, entry.stage ?? "stage", entry.kind ?? "artifact", entry.name ?? "pending"].join("-");
}

export function manifestArtifactRows(summary: JobManifestSummary | null | undefined, limit = 8): ManifestArtifactRow[] {
  const artifacts = summary?.important_artifacts ?? {};
  const keyCounts = new Map<string, number>();

  return Object.entries(artifacts)
    .flatMap(([group, value]) =>
      artifactEntries(value).map((entry) => {
        const baseKey = artifactKey(group, entry);
        const count = keyCounts.get(baseKey) ?? 0;
        keyCounts.set(baseKey, count + 1);

        return {
          key: count === 0 ? baseKey : `${baseKey}-${count + 1}`,
          label: group.replaceAll("_", " "),
          value: entry.name ?? "Pending",
          meta: `${entry.stage ?? "stage"} | ${entry.kind ?? "artifact"} | ${entry.exists ? "written" : "pending"}`,
        };
      }),
    )
    .slice(0, limit);
}

export function resultManifestArtifactRows(result: ProcessingResult | null, limit = 10) {
  return manifestArtifactRows(result?.manifestSummary, limit);
}
