"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher, del } from "@/lib/api";
import type { SongsResponse } from "@/lib/types";
import {
  PageHeader,
  Card,
  Input,
  Button,
  Spinner,
  EmptyState,
  Badge,
  fmtNum,
} from "@/components/ui";

const PAGE = 50;

export default function SongsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState<number | null>(null);

  const key = `/api/songs?q=${encodeURIComponent(q)}&limit=${PAGE}&offset=${
    page * PAGE
  }`;
  const { data, isLoading, mutate } = useSWR<SongsResponse>(key, fetcher);

  async function remove(id: number, title: string) {
    if (!confirm(`Supprimer « ${title} » et toutes ses empreintes ?`)) return;
    setBusy(id);
    try {
      await del(`/api/songs/${id}`);
      await mutate();
    } catch (e) {
      alert("Suppression impossible : " + (e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <>
      <PageHeader
        title="Morceaux indexés"
        subtitle="Le catalogue d'empreintes : ce que le moteur sait reconnaître. Aucun audio stocké."
      />

      <div className="mb-4 flex items-center gap-3">
        <Input
          placeholder="Rechercher un titre ou un artiste…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(0);
          }}
          className="max-w-sm"
        />
        <span className="text-sm text-faint">{fmtNum(total)} morceau(x)</span>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-muted">
          <Spinner /> Chargement…
        </div>
      ) : !data || data.songs.length === 0 ? (
        <EmptyState
          title="Aucun morceau"
          hint={q ? "Aucun résultat pour cette recherche." : "Indexez un premier morceau depuis l'onglet Ingestion."}
        />
      ) : (
        <Card className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-faint">
                <th className="px-4 py-3 font-medium">Titre</th>
                <th className="px-4 py-3 font-medium">Artiste</th>
                <th className="px-4 py-3 text-right font-medium">Empreintes</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.songs.map((s) => (
                <tr key={s.id} className="hover:bg-panel-2/40">
                  <td className="px-4 py-3 font-medium">{s.title}</td>
                  <td className="px-4 py-3 text-muted">{s.artist || "—"}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-muted">
                    {fmtNum(s.fingerprints)}
                  </td>
                  <td className="max-w-[14rem] px-4 py-3">
                    {s.source && s.source.startsWith("http") ? (
                      <a
                        href={s.source}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate text-vert hover:underline"
                        title={s.source}
                      >
                        {s.source}
                      </a>
                    ) : (
                      <Badge>{s.source || "—"}</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="danger"
                      onClick={() => remove(s.id, s.title)}
                      disabled={busy === s.id}
                    >
                      {busy === s.id ? <Spinner /> : "Supprimer"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {pages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3 text-sm">
          <Button
            variant="ghost"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            ← Précédent
          </Button>
          <span className="text-muted">
            Page {page + 1} / {pages}
          </span>
          <Button
            variant="ghost"
            disabled={page + 1 >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Suivant →
          </Button>
        </div>
      )}
    </>
  );
}
