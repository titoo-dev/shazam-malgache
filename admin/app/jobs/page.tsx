"use client";

import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import type { JobsResponse } from "@/lib/types";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { JobItem } from "@/components/JobItem";

export default function JobsPage() {
  // Polling à 2 s : reflète l'avancement du pipeline en quasi temps réel.
  const { data, error, isLoading } = useSWR<JobsResponse>(
    "/api/jobs?limit=100",
    fetcher,
    { refreshInterval: 2000 }
  );

  const jobs = data?.jobs ?? [];
  const active = jobs.filter(
    (j) => j.status === "running" || j.status === "queued"
  );
  const finished = jobs.filter(
    (j) => j.status === "done" || j.status === "error"
  );

  return (
    <>
      <PageHeader
        title="Pipeline / Jobs"
        subtitle="Suivi en temps réel des ingestions. Mise à jour automatique toutes les 2 s."
        action={
          <Link
            href="/ingest"
            className="rounded-lg bg-vert-deep px-4 py-2 text-sm font-medium text-white hover:bg-vert"
          >
            + Nouvelle ingestion
          </Link>
        }
      />

      {error ? (
        <EmptyState title="Backend injoignable" />
      ) : isLoading ? (
        <div className="flex items-center gap-2 text-muted">
          <Spinner /> Chargement…
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          title="Aucun job"
          hint="Lancez une ingestion pour voir le pipeline tourner ici."
        />
      ) : (
        <div className="space-y-8">
          <section>
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-faint">
              En cours
              {active.length > 0 && (
                <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400">
                  {active.length}
                </span>
              )}
            </h2>
            {active.length > 0 ? (
              <div className="space-y-3">
                {active.map((j) => (
                  <JobItem key={j.id} job={j} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-faint">Aucune ingestion en cours.</p>
            )}
          </section>

          {finished.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-faint">
                Historique
              </h2>
              <div className="space-y-3">
                {finished.map((j) => (
                  <JobItem key={j.id} job={j} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
