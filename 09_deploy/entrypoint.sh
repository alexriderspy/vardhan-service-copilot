#!/usr/bin/env bash
# Prepare everything the app needs (only what's missing), then start the UI.
set -euo pipefail

echo "Waiting for Postgres..."
until python -c "from sqlalchemy import create_engine; create_engine('$DATABASE_URL').connect()" 2>/dev/null; do sleep 2; done

[ -f artifacts/legacy/legacy.db ] || python 01_legacy_data/generate_legacy.py
python 02_migration/migrate.py                      # idempotent: rebuilds tables, views and the agent role
[ -f artifacts/mock_gmail.json ] || python 05_mcp_servers/seed_mock_data.py
if [ ! -f artifacts/intent_model/config.json ]; then
  python 03_classifier/generate_emails.py
  python 03_classifier/train.py --epochs 1
fi
[ -d artifacts/chroma ] || python 04_rag/build_index.py

exec streamlit run 07_app/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
