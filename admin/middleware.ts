import { NextRequest, NextResponse } from "next/server";

// Basic-auth de toute l'interface de gestion. Activé uniquement si ADMIN_USER
// et ADMIN_PASSWORD sont définis (lus à l'exécution, pas figés au build) ; sinon
// l'accès reste libre (dev local). Une fois authentifié, le navigateur renvoie
// l'en-tête Authorization sur les appels /api/* que Next reverse-proxie vers
// l'API (laquelle revérifie les mêmes identifiants).
export function middleware(req: NextRequest) {
  const user = process.env.ADMIN_USER;
  const pwd = process.env.ADMIN_PASSWORD;
  if (!user || !pwd) return NextResponse.next();

  const header = req.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const sep = decoded.indexOf(":");
      const u = decoded.slice(0, sep);
      const p = decoded.slice(sep + 1);
      if (u === user && p === pwd) return NextResponse.next();
    } catch {
      // en-tête malformé -> on retombe sur le challenge
    }
  }

  // NB : la valeur d'en-tête doit rester en ASCII/Latin-1 (pas de tiret cadratin).
  return new NextResponse("Authentification requise", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Shazam Malgache Admin"' },
  });
}

export const config = {
  // tout sauf les assets statiques de Next
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
