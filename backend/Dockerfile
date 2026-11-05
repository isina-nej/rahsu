FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgdal-dev libgeos-dev libproj-dev ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY backend ./backend
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
RUN groupadd -r app && useradd -r -g app app && chown -R app:app /app
USER app
WORKDIR /app/backend
CMD ["gunicorn","config.wsgi:application","-b","0.0.0.0:8000","--workers","2","--access-logfile","-"]
