import Link from "next/link";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-panel/70 p-5 ${className}`}
    >
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  href,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  href?: string;
}) {
  const inner = (
    <Card className="h-full transition-colors hover:border-vert/50">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-2 text-3xl font-bold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-faint">{hint}</div>}
    </Card>
  );
  return href ? (
    <Link href={href} className="block">
      {inner}
    </Link>
  ) : (
    inner
  );
}

const TONE: Record<string, string> = {
  vert: "bg-vert-deep/20 text-vert ring-vert/40",
  rouge: "bg-rouge/15 text-rouge ring-rouge/40",
  amber: "bg-amber-500/15 text-amber-400 ring-amber-500/40",
  slate: "bg-panel-2 text-muted ring-border",
};

export function Badge({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: keyof typeof TONE | string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${
        TONE[tone] ?? TONE.slate
      }`}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger";
}) {
  const styles = {
    primary:
      "bg-vert-deep text-white hover:bg-vert disabled:opacity-50 disabled:hover:bg-vert-deep",
    ghost: "border border-border text-muted hover:text-ink hover:border-faint",
    danger: "text-rouge hover:bg-rouge/10",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-border bg-panel-2 px-3 py-2 text-sm text-ink placeholder:text-faint outline-none focus:border-vert/60 focus:ring-1 focus:ring-vert/40 ${
        props.className ?? ""
      }`}
    />
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-faint border-t-vert ${className}`}
    />
  );
}

export function EmptyState({
  title,
  hint,
}: {
  title: string;
  hint?: string;
}) {
  return (
    <Card className="text-center text-muted">
      <div className="py-6">
        <div className="font-medium text-ink">{title}</div>
        {hint && <div className="mt-1 text-sm text-faint">{hint}</div>}
      </div>
    </Card>
  );
}

export function fmtNum(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("fr-FR");
}
