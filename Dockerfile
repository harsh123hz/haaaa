FROM node:22-bookworm-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
ENV VITE_ASSET_BASE=/static/
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_DEBUG=0
ENV DJANGO_ALLOWED_HOSTS=*
ENV PORT=10000

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./backend/staticfiles/
COPY deploy/start.sh ./deploy/start.sh
RUN chmod +x ./deploy/start.sh

WORKDIR /app/backend
CMD ["../deploy/start.sh"]

