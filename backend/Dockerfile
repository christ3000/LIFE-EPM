# Prépare l'image FastAPI et installe les dépendances du backend.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup --system lifeepm \
    && adduser --system --ingroup lifeepm lifeepm
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic
USER lifeepm
EXPOSE 8000
# Applique les migrations en attente avant de démarrer l'API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
