# syntax=docker/dockerfile:1

FROM node:24-alpine AS base
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable

FROM base AS manifests
WORKDIR /repo

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/backend/package.json apps/backend/package.json
COPY apps/mobile/package.json apps/mobile/package.json
COPY patches patches

FROM manifests AS build-dependencies
RUN pnpm install --frozen-lockfile --filter backend...

# A separate install from `manifests` rather than a second pass over
# `build-dependencies`, because pnpm leaves the dev dependencies behind in
# .pnpm when you install --prod on top of an existing full install.
FROM manifests AS production-dependencies
RUN pnpm install --frozen-lockfile --filter backend... --prod

FROM build-dependencies AS build
COPY tsconfig.base.json ./
COPY apps/backend apps/backend
RUN pnpm --filter backend build

FROM base AS runtime
ENV NODE_ENV=production
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 --ingroup nodejs hono

# pnpm links packages with relative symlinks, so the root and the package
# node_modules have to keep the same relative layout they had at install time.
COPY --from=production-dependencies --chown=hono:nodejs /repo/node_modules ./node_modules
COPY --from=production-dependencies --chown=hono:nodejs /repo/apps/backend/node_modules ./apps/backend/node_modules
COPY --from=production-dependencies --chown=hono:nodejs /repo/apps/backend/package.json ./apps/backend/package.json
COPY --from=build --chown=hono:nodejs /repo/apps/backend/dist ./apps/backend/dist
COPY --from=build --chown=hono:nodejs /repo/apps/backend/drizzle ./apps/backend/drizzle

WORKDIR /app/apps/backend
USER hono
EXPOSE 3000
CMD ["node", "dist/server.js"]
