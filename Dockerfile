FROM node:24-bookworm-slim AS signer
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --workspaces=false --ignore-scripts --no-audit --no-fund

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY --from=signer /usr/local/bin/node /usr/local/bin/node
COPY --from=signer /app/node_modules /app/node_modules
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt
COPY apps/api /app/apps/api
COPY scripts/sign-purchase.mjs /app/scripts/sign-purchase.mjs
COPY scripts/verify-nep413.mjs /app/scripts/verify-nep413.mjs
WORKDIR /app/apps/api
CMD ["sh", "-c", "alembic upgrade head && python -m restock.seed && exec uvicorn restock.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
