"use client";

import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import type { Stats, JobsResponse, SongsResponse } from "@/lib/types";
import {
  PageHeader,
  StatCard,
  Card,
  Spinner,
  EmptyState,
  fmtNum,
} from "@/components/ui";
import { JobItem } from "@/components/JobItem";

export default function Dashboard() {
  const { data: stats, error } = useSWR<Stats>("/api/stats", fetcher, {
    refreshInterval: 5000,
  });
  const { data: jobs } = useSWR<JobsResponse>("/api/jobs?limit=5", fetcher, {
    refreshInterval: 3000,
  });
  const { data: songs } = useSWR<SongsResponse>(
    "/api/songs?limit=5",
    fetcher
  );

  if (error) {
    return (
      <>
        <PageHeader title="Tableau de bord" />
        <EmptyState
          title="Backend injoignable"
          hint="Vérifiez que l'API tourne (API_URL) et rechargez."
        />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Tableau de bord"
        subtitle="Vue d'ensemble du moteur de reconnaissance et de ses catalogues."
        action={
          <Link
            href="/ingest"
            className="rounded-lg bg-vert-deep px-4 py-2 text-sm font-medium text-white hover:bg-vert"
          >
            + Ajouter un morceau
          </Link>
        }
      />

      {!stats ? (
        <div className="flex items-center gap-2 text-muted">
          <Spinner /> Chargement…
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            label="Morceaux indexés"
            value={fmtNum(stats.engine.songs)}
            hint="reconnaissables au micro"
            href="/songs"
          />
          <StatCard
            label="Empreintes"
            value={fmtNum(stats.engine.fingerprints)}
            hint={`~${fmtNum(stats.engine.avg_fingerprints)} / morceau`}
          />
          <StatCard
            label="Artistes au catalogue"
            value={fmtNum(stats.catalog.artists)}
            hint="référentiel Moozik"
            href="/catalog"
          />
          <StatCard
            label="Jobs actifs"
            value={fmtNum(stats.jobs_active)}
            hint="ingestions en cours"
            href="/jobs"
          />
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-faint">
              Ingestions récentes
            </h2>
            <Link href="/jobs" className="text-xs text-vert hover:underline">
              tout voir →
            </Link>
          </div>
          {jobs && jobs.jobs.length > 0 ? (
            <div className="space-y-3">
              {jobs.jobs.map((j) => (
                <JobItem key={j.id} job={j} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="Aucune ingestion"
              hint="Lancez-en une depuis l'onglet Ingestion."
            />
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-faint">
              Derniers morceaux
            </h2>
            <Link href="/songs" className="text-xs text-vert hover:underline">
              tout voir →
            </Link>
          </div>
          {songs && songs.songs.length > 0 ? (
            <Card className="divide-y divide-border p-0">
              {songs.songs.map((s) => (
                <div key={s.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {s.title}
                    </div>
                    <div className="truncate text-xs text-faint">
                      {s.artist || "—"}
                    </div>
                  </div>
                  <div className="text-xs tabular-nums text-muted">
                    {fmtNum(s.fingerprints)} empr.
                  </div>
                </div>
              ))}
            </Card>
          ) : (
            <EmptyState title="Base vide" hint="Aucun morceau indexé." />
          )}
        </section>
      </div>
    </>
  );
}
