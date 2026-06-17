import type { Job } from "@/lib/types";
import { Badge, fmtNum } from "./ui";
import { STAGE_LABEL, STATUS_LABEL, STATUS_TONE, fmtDate } from "@/lib/labels";

export function ProgressBar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel-2">
      <div
        className="h-full rounded-full bg-vert transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function JobItem({ job }: { job: Job }) {
  const running = job.status === "running" || job.status === "queued";
  return (
    <div className="rounded-lg border border-border bg-panel-2/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-medium">
            {job.title || job.url || "Sans titre"}
          </div>
          <div className="truncate text-xs text-faint">
            {job.artist ? `${job.artist} · ` : ""}
            {job.url || "fichier"}
          </div>
        </div>
        <Badge tone={STATUS_TONE[job.status]}>{STATUS_LABEL[job.status]}</Badge>
      </div>

      {running && (
        <div className="mt-3">
          <ProgressBar value={job.progress} />
          <div className="mt-1.5 flex items-center justify-between text-xs text-muted">
            <span>{job.stage ? STAGE_LABEL[job.stage] : ""}</span>
            <span className="tabular-nums">
              {Math.round(job.progress * 100)}%
            </span>
          </div>
        </div>
      )}

      <div className="mt-2 text-xs">
        {job.status === "done" && (
          <span className="text-vert">
            {fmtNum(job.fingerprints)} empreintes · audio jeté
          </span>
        )}
        {job.status === "error" && (
          <span className="text-rouge">{job.error || "échec"}</span>
        )}
        {running && <span className="text-muted">{job.message}</span>}
        <span className="float-right text-faint">{fmtDate(job.created_at)}</span>
      </div>
    </div>
  );
}
