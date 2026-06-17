# Interface de gestion Next.js — build standalone, image légère.
FROM node:22-alpine AS deps
WORKDIR /app
# La version de pnpm est figée via "packageManager" dans package.json : corepack
# la télécharge sans prompt, garantissant le même comportement qu'en local.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
# pnpm-workspace.yaml porte la config des build scripts (sharp approuvé) : sans
# lui, pnpm bloque l'install en environnement non-interactif (Docker).
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
# URL du backend, figée dans les rewrites au build (cf. next.config.mjs).
ARG API_URL=http://api:8000
ENV API_URL=$API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
# Sortie standalone : serveur Node minimal + dépendances strictement nécessaires.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
