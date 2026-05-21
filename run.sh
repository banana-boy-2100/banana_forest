#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  .env ファイルを作成しました。ANTHROPIC_API_KEY を設定してください。"
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

echo "🚀 サーバー起動: http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
