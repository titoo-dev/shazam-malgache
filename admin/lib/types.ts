// Types partagés avec l'API d'administration FastAPI (/api/*).

export type Stats = {
  engine: {
    songs: number;
    fingerprints: number;
    distinct_hashes: number;
    avg_fingerprints: number;
  };
  catalog: { available: boolean; artists: number; tracks: number };
  jobs_active: number;
};

export type Song = {
  id: number;
  title: string;
  artist: string | null;
  source: string | null;
  fingerprints: number;
};

export type SongDetail = Song & {
  distinct_hashes: number;
};

export type SongsResponse = { total: number; songs: Song[] };

export type Artist = {
  id: number;
  artist_name: string;
  slug: string;
  audio_count: number;
  play_count: number;
  rank: number;
  isni_code: string | null;
  ipi_code: string | null;
  uuid: string;
};

export type ArtistsResponse = {
  total: number;
  available: boolean;
  artists: Artist[];
};

export type JobStatus = "queued" | "running" | "done" | "error";
export type JobStage =
  | "queued"
  | "metadata"
  | "download"
  | "decode"
  | "fingerprint"
  | "store"
  | "done";

export type Job = {
  id: string;
  kind: "url" | "file";
  url: string | null;
  title: string | null;
  artist: string | null;
  status: JobStatus;
  stage: JobStage | null;
  progress: number;
  message: string | null;
  song_id: number | null;
  fingerprints: number | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type JobsResponse = { jobs: Job[] };

export type ProbeResult = {
  title: string;
  uploader: string;
  duration: string;
};
