FROM node:24-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=/api
ENV INTERNAL_API_URL=http://api:8000
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY contracts/procurement-policy/package.json contracts/procurement-policy/package.json
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY apps/web apps/web
COPY packages/shared packages/shared
RUN npm run build

FROM node:24-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV INTERNAL_API_URL=http://api:8000
COPY --from=build --chown=node:node /app/node_modules node_modules
COPY --from=build --chown=node:node /app/apps/web apps/web
USER node
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["../../node_modules/.bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
