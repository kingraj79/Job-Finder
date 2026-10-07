#!/usr/bin/env bash
# One-command start: sets up the environment on first run, then launches the dashboard.
# Usage: ./start.sh            (opens on http://localhost:8000)
#        PORT=9000 ./start.sh  (use a different port)
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required but wasn't found. Install it from https://www.python.org/downloads/" >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "First run: creating a virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Checking dependencies..."
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from the template. Add your Adzuna keys there if you want that job source."
fi

echo "Starting Job Finder at http://localhost:${PORT}  (press Ctrl+C to stop)"
exec uvicorn job_finder.webapp:app --host 127.0.0.1 --port "${PORT}"
