#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the Python-side development experience:
# the AI control plane (Python 3.14) and the static quality gates. The
# Docker-backed Frappe/ERPNext stack is a separate on-demand path documented in
# development/README.md and is not provisioned here.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Python 3.14 satisfies services/ai_control_plane/pyproject.toml (requires-python >=3.14).
uv python install 3.14

if [ ! -x .venv/bin/python ]; then
  uv venv --python 3.14 .venv
fi

uv pip install --python .venv/bin/python ./services/ai_control_plane

# Local-only dev env for scripts/dev.sh; placeholders only, never real secrets.
if [ ! -f development/.env ]; then
  cp development/.env.example development/.env
fi

echo "Cloud Agent install complete."
echo "Activate the control-plane venv with: source .venv/bin/activate"
