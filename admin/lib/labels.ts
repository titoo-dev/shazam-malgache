import type { JobStage, JobStatus } from "./types";

export const STAGE_LABEL: Record<JobStage, string> = {
  queued: "En attente",
  metadata: "Métadonnées",
  download: "Téléchargement",
  decode: "Décodage",
  fingerprint: "Empreinte",
  store: "Stockage",
  done: "Terminé",
};

export const STATUS_LABEL: Record<JobStatus, string> = {
  queued: "En attente",
  running: "En cours",
  done: "Terminé",
  error: "Échec",
};

export const STATUS_TONE: Record<JobStatus, string> = {
  queued: "slate",
  running: "amber",
  done: "vert",
  error: "rouge",
};

export function fmtDuration(seconds: string | number | null): string {
  const s = Number(seconds);
  if (!Number.isFinite(s) || s <= 0) return "—";
  const m = Math.floor(s / 60);
  const r = Math.round(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}

export function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
