#!/usr/bin/env bash
# Cloud Agent environment bootstrap for Daily Stock Analysis.
# Idempotent: safe to re-run. Installs backend + frontend dependencies and
# builds the web bundle that the FastAPI backend serves.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Installing system packages (python tooling, CJK fonts, wkhtmltopdf)"
# wkhtmltopdf ships wkhtmltoimage, used for Markdown-to-image report rendering
# (see docker/Dockerfile). python-is-python3 lets repo scripts call `python`.
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  python-is-python3 \
  python3-pip \
  wkhtmltopdf \
  fontconfig \
  fonts-noto-cjk

echo "==> Installing backend Python dependencies"
# Mirrors CI (.github/requirements-ci.txt = requirements.txt + flake8/pytest).
# --break-system-packages installs into the user site on Ubuntu's PEP 668
# managed interpreter, matching how the Docker image installs requirements.
python -m pip install --break-system-packages --upgrade pip
python -m pip install --break-system-packages -r .github/requirements-ci.txt

echo "==> Installing web dependencies and building the frontend bundle"
cd apps/dsa-web
npm ci
npm run build

echo "==> Environment setup complete"
