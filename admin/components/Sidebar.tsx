"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Tableau de bord", icon: "▦" },
  { href: "/songs", label: "Morceaux indexés", icon: "♪" },
  { href: "/catalog", label: "Catalogue artistes", icon: "☆" },
  { href: "/ingest", label: "Ingestion", icon: "↧" },
  { href: "/jobs", label: "Pipeline / Jobs", icon: "⚙" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-panel/60 backdrop-blur px-4 py-6 hidden md:flex md:flex-col gap-6">
      <Link href="/" className="flex items-center gap-2 px-2">
        <span className="flex h-7 w-10 overflow-hidden rounded-sm shadow">
          <span className="flex-1 bg-white" />
          <span className="flex flex-1 flex-col">
            <span className="flex-1 bg-rouge" />
            <span className="flex-1 bg-vert-deep" />
          </span>
        </span>
        <span className="font-semibold leading-tight">
          Shazam
          <br />
          <span className="text-muted text-sm font-normal">Malgache</span>
        </span>
      </Link>

      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-vert-deep/20 text-ink ring-1 ring-vert/40"
                  : "text-muted hover:bg-panel-2 hover:text-ink"
              }`}
            >
              <span className="w-4 text-center text-faint">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-2 text-xs leading-relaxed text-faint">
        On ne stocke jamais d&apos;audio — uniquement des empreintes
        irréversibles.
      </div>
    </aside>
  );
}
