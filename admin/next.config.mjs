/** @type {import('next').NextConfig} */

// L'interface appelle l'API via des chemins relatifs `/api/*`. Next les
// reverse-proxy vers le backend FastAPI : pas de CORS, pas d'URL en dur côté
// navigateur. La cible est lue dans API_URL (par défaut localhost:8000 en dev,
// http://api:8000 dans docker-compose). La valeur est figée au build.
const API_URL = process.env.API_URL || "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
