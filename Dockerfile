# DealLens — deployable container (Railway / any Docker host).
# The app is pure Python standard library, so the image is tiny and has no
# pip dependencies. python-docx is optional (Word reports) and installed for
# convenience; remove it to shrink further.
FROM python:3.12-slim

WORKDIR /app

# Copy the whole platform (all deallens_* packages + the UI/gateway).
COPY . /app

# Optional extras: Word (.docx) reports and PDF statement reading.
# Everything else needs no dependencies.
RUN pip install --no-cache-dir python-docx==1.2.0 pdfplumber==0.11.4 || true

# The gateway finds sibling packages relative to this directory.
ENV DEALLENS_HOME=/app
# Persist deals in SQLite on a mounted volume (see railway.toml / DEPLOY.md).
ENV DEALLENS_DB=/data/deallens.db
ENV HOST=0.0.0.0
# Railway injects $PORT; default to 8765 for local `docker run`.
ENV PORT=8765

# Run from the gateway package directory so `python -m ui` resolves.
WORKDIR /app/deallens_ui

EXPOSE 8765
# Shell form so $PORT expands at runtime.
CMD python -m ui --host 0.0.0.0 --port ${PORT:-8765}
