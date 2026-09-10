#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🤖 CrewAI Studio – Dev setup"
echo "────────────────────────────"

cd "$PROJECT_DIR"

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "⬆️  Installing dependencies..."
pip install -e ".[dev]" --quiet

# Copy env if not present
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "📝 Created .env from .env.example – please add your API keys!"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API key(s)"
echo "  2. source .venv/bin/activate"
echo "  3. python main.py"
echo "  4. Open http://localhost:8000"
