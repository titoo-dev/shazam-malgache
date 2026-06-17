"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import type { ArtistsResponse } from "@/lib/types";
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
const SORTS = [
  { key: "rank", label: "Popularité (rang)" },
  { key: "name", label: "Nom (A→Z)" },
  { key: "tracks", label: "Nb de titres" },
  { key: "plays", label: "Écoutes" },
];

export default function CatalogPage() {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("rank");
  const [page, setPage] = useState(0);

  const key = `/api/catalog/artists?q=${encodeURIComponent(
    q
  )}&sort=${sort}&limit=${PAGE}&offset=${page * PAGE}`;
  const { data, isLoading } = useSWR<ArtistsResponse>(key, fetcher);

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <>
      <PageHeader
        title="Catalogue artistes"
        subtitle="Référentiel des artistes malgaches (métadonnées publiques Moozik). Sert à repérer qui indexer."
      />

      {data && !data.available ? (
        <EmptyState
          title="Catalogue indisponible"
          hint="Le fichier catalog.db est absent. Construisez-le via research/catalog.py."
        />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Input
              placeholder="Rechercher un artiste…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(0);
              }}
              className="max-w-sm"
            />
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-border bg-panel-2 px-3 py-2 text-sm text-ink outline-none focus:border-vert/60"
            >
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>
                  Trier : {s.label}
                </option>
              ))}
            </select>
            <span className="text-sm text-faint">
              {fmtNum(total)} artiste(s)
            </span>
          </div>

          {isLoading ? (
            <div className="flex items-center gap-2 text-muted">
              <Spinner /> Chargement…
            </div>
          ) : !data || data.artists.length === 0 ? (
            <EmptyState title="Aucun artiste" hint="Aucun résultat." />
          ) : (
            <Card className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-faint">
                    <th className="px-4 py-3 font-medium">Artiste</th>
                    <th className="px-4 py-3 text-right font-medium">Rang</th>
                    <th className="px-4 py-3 text-right font-medium">Titres</th>
                    <th className="px-4 py-3 font-medium">ISNI / IPI</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.artists.map((a) => (
                    <tr key={a.id} className="hover:bg-panel-2/40">
                      <td className="px-4 py-3">
                        <div className="font-medium">{a.artist_name}</div>
                        <div className="text-xs text-faint">{a.slug}</div>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted">
                        #{a.rank}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted">
                        {a.audio_count || "—"}
                      </td>
                      <td className="px-4 py-3">
                        {a.isni_code || a.ipi_code ? (
                          <span className="text-xs text-muted">
                            {a.isni_code || a.ipi_code}
                          </span>
                        ) : (
                          <Badge>non renseigné</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <a
                            href={`https://www.youtube.com/results?search_query=${encodeURIComponent(
                              a.artist_name
                            )}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-faint hover:text-ink"
                          >
                            YouTube ↗
                          </a>
                          <Link
                            href={`/ingest?artist=${encodeURIComponent(
                              a.artist_name
                            )}`}
                            className="text-xs text-vert hover:underline"
                          >
                            Indexer →
                          </Link>
                        </div>
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
      )}
    </>
  );
}
