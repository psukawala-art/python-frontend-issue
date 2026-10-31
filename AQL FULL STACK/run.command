#!/bin/bash
# ==========================================================
#  AirScope - one-shot launcher, macOS only
#
#  Start it either way:
#    - Terminal:   cd into this folder, then   ./run.command
#    - Finder:     double-click run.command
#
#  It: finds Python 3 -> creates .venv (first run) -> installs packages
#      -> checks the backend -> starts the dashboard -> opens your browser.
#  Press Ctrl+C (or close the window) to stop everything.
# ==========================================================
set -eu

cd "$(dirname "$0")"
VENV_DIR="$(pwd)/.venv"

say()  { printf '\033[1;32m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m!!\033[0m  %s\n' "$1"; }
die()  {
  printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2
  if [ -t 0 ]; then read -r -p "Press Enter to close..." _ || true; fi
  exit 1
}

# ---- macOS only ----
[ "$(uname -s)" = "Darwin" ] || die "This launcher is for macOS only."

# ---- project files ----
for f in app.py aqi_backend.py requirements.txt; do
  [ -f "$f" ] || die "$f is missing. Keep all AirScope files in one folder."
done

# ---- remove Apple's "downloaded from the internet" flag from this folder ----
xattr -dr com.apple.quarantine . 2>/dev/null || true

# ---- find a real Python 3 (newest first; Homebrew, python.org, then system) ----
PYTHON_BIN=""
for c in python3.13 python3.12 python3.11 python3.10 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
         python3; do
  p="$(command -v "$c" 2>/dev/null || true)"
  [ -n "$p" ] || continue
  # Apple's /usr/bin/python3 is only a stub until Command Line Tools are installed
  if [ "$p" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1; then
    continue
  fi
  if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PYTHON_BIN="$p"
    break
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  die "No usable Python 3 found. Install it from https://www.python.org/downloads/macos/ (or: brew install python), then run this again."
fi
say "Using $("$PYTHON_BIN" --version 2>&1) ($PYTHON_BIN)"

# ---- virtual environment (rebuilt automatically if its Python disappeared) ----
if [ -x "$VENV_DIR/bin/python" ] && ! "$VENV_DIR/bin/python" -c 'pass' 2>/dev/null; then
  warn "Existing .venv is broken; recreating it."
  rm -rf "$VENV_DIR"
fi
if [ ! -x "$VENV_DIR/bin/python" ]; then
  say "Creating virtual environment (first run only)..."
  "$PYTHON_BIN" -m venv "$VENV_DIR" || die "Could not create the virtual environment."
fi
PY="$VENV_DIR/bin/python"

# ---- packages (reinstalled only when requirements.txt changes) ----
REQ_HASH="$(shasum requirements.txt | awk '{print $1}')"
HASH_FILE="$VENV_DIR/.requirements.sha"
if [ ! -f "$HASH_FILE" ] || [ "$(cat "$HASH_FILE")" != "$REQ_HASH" ]; then
  say "Installing packages (needs internet, can take a minute)..."
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r requirements.txt \
    || die "Package installation failed. Check your internet connection and run again."
  echo "$REQ_HASH" > "$HASH_FILE"
else
  say "Packages already installed."
fi

# ---- backend self-check (offline-safe: uses the built-in demo data) ----
say "Checking the backend..."
"$PY" - <<'PYCHECK' || die "Backend self-check failed - see the error above."
import aqi_backend as a
daily = a.calculate_aqi(a.make_demo_data("Pune"))
future = a.predict_aqi(list(daily["AQI"]), days=3)
assert len(future) == 3 and len(a.cities) > 0
print("    backend OK: %d cities, AQI engine and 3-day predictor working" % len(a.cities))
PYCHECK

# ---- free port ----
PORT=8501
while lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
  PORT=$((PORT + 1))
  [ "$PORT" -le 8520 ] || die "No free port between 8501 and 8520."
done

# ---- start dashboard (frontend, which loads the backend module) ----
say "Starting AirScope on http://localhost:$PORT ..."
"$PY" -m streamlit run app.py \
  --server.port "$PORT" \
  --server.headless true \
  --browser.gatherUsageStats false &
SERVER_PID=$!

cleanup() {
  trap - INT TERM HUP EXIT
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo
    say "Stopping AirScope..."
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup INT TERM HUP EXIT

# ---- wait for the server, then open the browser ----
READY=0
for _ in $(seq 1 60); do
  kill -0 "$SERVER_PID" 2>/dev/null || die "Streamlit stopped unexpectedly - see the error above."
  if curl -fs "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1; then READY=1; break; fi
  sleep 1
done
[ "$READY" -eq 1 ] || warn "Server is slow to start; opening the browser anyway."

say "AirScope is running. Press Ctrl+C here to stop."
open "http://localhost:$PORT" || warn "Open http://localhost:$PORT in your browser."

wait "$SERVER_PID"
