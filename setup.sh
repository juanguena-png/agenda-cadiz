#!/usr/bin/env bash
# Configuración del entorno cloud "agenda-cadiz". Idempotente. Úsalo como script de configuración del entorno.
set -euo pipefail
cd "$(dirname "$0")"

pip install -q -r requirements.txt

# ffmpeg (reels)
if ! command -v ffmpeg >/dev/null 2>&1; then
  (apt-get update -qq && apt-get install -y -qq ffmpeg) || sudo apt-get install -y -qq ffmpeg
fi

# Fuentes tipográficas (Inter) para que las plantillas se vean igual en cualquier entorno
if ! fc-list | grep -qi "Inter"; then
  (apt-get install -y -qq fonts-inter) || echo "AVISO: no se pudo instalar fonts-inter; se usará la fuente de reserva"
fi

# Chromium para Playwright. En el entorno cloud ya viene preinstalado en /opt/pw-browsers
# (render.py lo detecta); si no existe, se descarga el de Playwright.
if [ ! -x /opt/pw-browsers/chromium/chrome-linux64/chrome ] && ! ls /opt/pw-browsers/chromium-*/chrome-linux64/chrome >/dev/null 2>&1; then
  python -m playwright install --with-deps chromium
fi

mkdir -p posts registros patrocinadores musica
echo "Entorno listo."
