#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
ROOT="$(cd "$(dirname "$0")" && pwd)"
PG_BIN="$(brew --prefix)/opt/postgresql@16/bin"
export PATH="$PG_BIN:$PATH"

# Ensure postgres is up
brew services start postgresql@16 2>/dev/null || true

# Clean up any previous PIDs
BACKEND_PID_FILE="/tmp/insight_backend.pid"
DASHBOARD_PID_FILE="/tmp/insight_dashboard.pid"
PATIENT_PID_FILE="/tmp/insight_patient.pid"

stop_all() {
  echo -e "\n${GREEN}Stopping all services…${NC}"
  [ -f "$BACKEND_PID_FILE" ]  && kill "$(cat $BACKEND_PID_FILE)"  2>/dev/null || true
  [ -f "$DASHBOARD_PID_FILE" ] && kill "$(cat $DASHBOARD_PID_FILE)" 2>/dev/null || true
  [ -f "$PATIENT_PID_FILE" ]  && kill "$(cat $PATIENT_PID_FILE)"  2>/dev/null || true
  rm -f "$BACKEND_PID_FILE" "$DASHBOARD_PID_FILE" "$PATIENT_PID_FILE"
}
trap stop_all EXIT INT TERM

# ── Backend ───────────────────────────────────────────────────────────────────
echo -e "${GREEN}Starting backend…${NC}"
source "$ROOT/backend/.venv/bin/activate"
set -a; source "$ROOT/.env"; set +a
cd "$ROOT/backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > /tmp/insight_backend.log 2>&1 &
echo $! > "$BACKEND_PID_FILE"

# ── Clinician dashboard ───────────────────────────────────────────────────────
echo -e "${GREEN}Starting clinician dashboard…${NC}"
cd "$ROOT/clinician-dashboard"
VITE_API_URL=http://localhost:8000 npm run dev -- --port 5173 \
  > /tmp/insight_dashboard.log 2>&1 &
echo $! > "$DASHBOARD_PID_FILE"

# ── Patient app (web) ─────────────────────────────────────────────────────────
echo -e "${GREEN}Starting patient app…${NC}"
cd "$ROOT/patient-app"
EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web --port 8081 \
  > /tmp/insight_patient.log 2>&1 &
echo $! > "$PATIENT_PID_FILE"

# Wait for backend to be ready
echo -n "Waiting for backend"
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e " ${GREEN}ready${NC}"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ All services running${NC}"
echo ""
echo "  Backend API docs  →  http://localhost:8000/api/docs"
echo "  Clinician portal  →  http://localhost:5173"
echo "  Patient app (web) →  http://localhost:8081"
echo ""
echo "  Logs:"
echo "    tail -f /tmp/insight_backend.log"
echo "    tail -f /tmp/insight_dashboard.log"
echo "    tail -f /tmp/insight_patient.log"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Press Ctrl-C to stop everything."
echo ""

# Keep alive and tail logs
wait
