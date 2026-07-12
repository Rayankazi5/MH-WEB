#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step()  { echo -e "\n${GREEN}==>${NC} $1"; }
warn()  { echo -e "${YELLOW}  ⚠${NC}  $1"; }
die()   { echo -e "${RED}Error:${NC} $1"; exit 1; }

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── 1. Homebrew ───────────────────────────────────────────────────────────────
step "Checking Homebrew"
if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew (you may be prompted for your password)…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to current shell PATH (Apple Silicon default location)
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi
echo "  brew $(brew --version | head -1)"

# ── 2. PostgreSQL ─────────────────────────────────────────────────────────────
step "Installing PostgreSQL 16"
brew install postgresql@16 2>/dev/null || true

# Detect pg bin dir (Apple Silicon vs Intel)
PG_BIN="$(brew --prefix)/opt/postgresql@16/bin"
export PATH="$PG_BIN:$PATH"

brew services start postgresql@16
sleep 2   # let postgres settle

step "Creating database user and database"
createuser --superuser insight 2>/dev/null || true
psql postgres -c "ALTER USER insight WITH PASSWORD 'insight_dev';" 2>/dev/null || true
createdb -O insight insight_navigator 2>/dev/null || true
echo "  Database: insight_navigator"

# ── 3. Node.js ────────────────────────────────────────────────────────────────
step "Installing Node.js"
brew install node 2>/dev/null || true
echo "  node $(node --version)  npm $(npm --version)"

# ── 4. Python virtualenv + deps ───────────────────────────────────────────────
step "Setting up Python virtual environment"
python3 -m venv "$ROOT/backend/.venv"
source "$ROOT/backend/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$ROOT/backend/requirements.txt"
echo "  Installed $(pip list | wc -l | tr -d ' ') packages"

# ── 5. .env ───────────────────────────────────────────────────────────────────
step "Creating .env"
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
INTERNAL_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(16))")
JOURNAL_KEY=$(python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())")

# Update keys (macOS sed needs -i '')
sed -i '' "s|change_this_to_a_secure_random_string_in_production|$SECRET_KEY|" "$ROOT/.env"
sed -i '' "s|change_this_internal_secret_in_production|$INTERNAL_SECRET|" "$ROOT/.env"
sed -i '' "s|JOURNAL_ENCRYPTION_KEY=|JOURNAL_ENCRYPTION_KEY=$JOURNAL_KEY|" "$ROOT/.env"
# Point to local postgres (no Docker)
sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=postgresql://insight:insight_dev@localhost:5432/insight_navigator|" "$ROOT/.env"
# Patient app and dashboard point to local backend
sed -i '' "s|EXPO_PUBLIC_API_URL=.*|EXPO_PUBLIC_API_URL=http://localhost:8000|" "$ROOT/.env"
sed -i '' "s|VITE_API_URL=.*|VITE_API_URL=http://localhost:8000|" "$ROOT/.env"

echo "  .env written"
if ! grep -q "ANTHROPIC_API_KEY=." "$ROOT/.env"; then
  warn "ANTHROPIC_API_KEY is empty — narrative generation will fail. Add it to .env when ready."
fi

# ── 6. Alembic migrations ─────────────────────────────────────────────────────
step "Running database migrations"
cd "$ROOT/backend"
source .venv/bin/activate
set -a; source "$ROOT/.env"; set +a
alembic upgrade head
echo "  Migrations complete"

# ── 7. Frontend dependencies ──────────────────────────────────────────────────
step "Installing clinician dashboard dependencies"
cd "$ROOT/clinician-dashboard"
npm install --silent

step "Installing patient app dependencies"
cd "$ROOT/patient-app"
npm install --silent

# ── Done ──────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Run this to start everything:"
echo ""
echo "  bash $ROOT/start.sh"
