"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { post, postForm } from "@/lib/api";
import type { Job, ProbeResult } from "@/lib/types";
import { fmtDuration } from "@/lib/labels";
import {
  PageHeader,
  Card,
  Input,
  Button,
  Spinner,
  Badge,
} from "@/components/ui";

type Tab = "url" | "batch" | "file";

function Banner({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <div className="mb-6 flex items-center justify-between rounded-lg border border-vert/40 bg-vert-deep/15 px-4 py-3 text-sm">
      <span>
        {count} ingestion(s) lancée(s). L&apos;audio est téléchargé puis jeté ;
        seules les empreintes sont conservées.
      </span>
      <Link href="/jobs" className="font-medium text-vert hover:underline">
        Suivre le pipeline →
      </Link>
    </div>
  );
}

function Tabs({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const items: { key: Tab; label: string }[] = [
    { key: "url", label: "Lien YouTube" },
    { key: "batch", label: "Plusieurs liens" },
    { key: "file", label: "Fichier audio" },
  ];
  return (
    <div className="mb-6 inline-flex rounded-lg border border-border bg-panel-2/50 p-1">
      {items.map((it) => (
        <button
          key={it.key}
          onClick={() => setTab(it.key)}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
            tab === it.key
              ? "bg-vert-deep text-white"
              : "text-muted hover:text-ink"
          }`}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

function UrlForm({ onDone }: { onDone: (n: number) => void }) {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  const [probing, setProbing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  async function doProbe() {
    if (!url.trim()) return;
    setProbing(true);
    setErr("");
    setProbe(null);
    try {
      const r = await post<ProbeResult>("/api/youtube/probe", { url });
      setProbe(r);
      if (!title) setTitle(r.title);
      if (!artist) setArtist(r.uploader);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setProbing(false);
    }
  }

  async function submit() {
    if (!url.trim()) return;
    setSubmitting(true);
    setErr("");
    try {
      await post<Job>("/api/jobs", { url, title, artist });
      setUrl("");
      setTitle("");
      setArtist("");
      setProbe(null);
      onDone(1);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="max-w-xl space-y-4">
      <div>
        <label className="mb-1 block text-sm text-muted">Lien YouTube</label>
        <div className="flex gap-2">
          <Input
            placeholder="https://youtu.be/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doProbe()}
          />
          <Button variant="ghost" onClick={doProbe} disabled={probing || !url}>
            {probing ? <Spinner /> : "Sonder"}
          </Button>
        </div>
        <p className="mt-1 text-xs text-faint">
          « Sonder » lit le titre/l&apos;artiste sans rien télécharger.
        </p>
      </div>

      {probe && (
        <div className="text-xs text-muted">
          <Badge tone="vert">trouvé</Badge>{" "}
          <span className="ml-1">
            {probe.title} · {probe.uploader} · {fmtDuration(probe.duration)}
          </span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-muted">Titre</label>
          <Input
            placeholder="(auto si vide)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Artiste</label>
          <Input
            placeholder="(auto si vide)"
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
          />
        </div>
      </div>

      {err && <p className="text-sm text-rouge">{err}</p>}

      <Button onClick={submit} disabled={submitting || !url}>
        {submitting ? <Spinner /> : "Lancer l'ingestion"}
      </Button>
    </Card>
  );
}

function BatchForm({
  onDone,
  defaultArtist,
}: {
  onDone: (n: number) => void;
  defaultArtist: string;
}) {
  const [text, setText] = useState("");
  const [artist, setArtist] = useState(defaultArtist);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => setArtist(defaultArtist), [defaultArtist]);

  const urls = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  async function submit() {
    if (urls.length === 0) return;
    setSubmitting(true);
    setErr("");
    try {
      const r = await post<{ count: number }>("/api/jobs/batch", {
        urls,
        artist,
      });
      setText("");
      onDone(r.count);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="max-w-xl space-y-4">
      <div>
        <label className="mb-1 block text-sm text-muted">
          Liens YouTube (un par ligne)
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          placeholder={"https://youtu.be/…\nhttps://youtu.be/…"}
          className="w-full rounded-lg border border-border bg-panel-2 px-3 py-2 font-mono text-sm text-ink placeholder:text-faint outline-none focus:border-vert/60 focus:ring-1 focus:ring-vert/40"
        />
        <p className="mt-1 text-xs text-faint">
          {urls.length} lien(s) — le titre/l&apos;artiste de chacun seront lus
          automatiquement.
        </p>
      </div>
      <div>
        <label className="mb-1 block text-sm text-muted">
          Artiste commun (optionnel)
        </label>
        <Input
          placeholder="appliqué à tous les liens"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {err && <p className="text-sm text-rouge">{err}</p>}

      <Button onClick={submit} disabled={submitting || urls.length === 0}>
        {submitting ? <Spinner /> : `Ingérer ${urls.length || ""} lien(s)`}
      </Button>
    </Card>
  );
}

function FileForm({ onDone }: { onDone: (n: number) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    if (!file) return;
    setSubmitting(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("title", title);
      fd.append("artist", artist);
      await postForm<Job>("/api/jobs/file", fd);
      setFile(null);
      setTitle("");
      setArtist("");
      onDone(1);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="max-w-xl space-y-4">
      <div>
        <label className="mb-1 block text-sm text-muted">Fichier audio</label>
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-vert-deep file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-vert"
        />
        <p className="mt-1 text-xs text-faint">
          Lu uniquement pour calculer l&apos;empreinte, puis supprimé.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-muted">Titre</label>
          <Input
            placeholder="(nom du fichier si vide)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Artiste</label>
          <Input value={artist} onChange={(e) => setArtist(e.target.value)} />
        </div>
      </div>

      {err && <p className="text-sm text-rouge">{err}</p>}

      <Button onClick={submit} disabled={submitting || !file}>
        {submitting ? <Spinner /> : "Lancer l'ingestion"}
      </Button>
    </Card>
  );
}

function IngestInner() {
  const params = useSearchParams();
  const prefillArtist = params.get("artist") ?? "";
  const [tab, setTab] = useState<Tab>(prefillArtist ? "batch" : "url");
  const [done, setDone] = useState(0);

  return (
    <>
      <PageHeader
        title="Ingestion"
        subtitle="Le pipeline : téléchargement → décodage → empreinte → stockage. L'audio est jeté à la fin."
      />
      <Banner count={done} />
      <Tabs tab={tab} setTab={setTab} />

      {tab === "url" && <UrlForm onDone={(n) => setDone((d) => d + n)} />}
      {tab === "batch" && (
        <BatchForm
          onDone={(n) => setDone((d) => d + n)}
          defaultArtist={prefillArtist}
        />
      )}
      {tab === "file" && <FileForm onDone={(n) => setDone((d) => d + n)} />}
    </>
  );
}

export default function IngestPage() {
  return (
    <Suspense fallback={<PageHeader title="Ingestion" />}>
      <IngestInner />
    </Suspense>
  );
}
