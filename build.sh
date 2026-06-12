#!/usr/bin/env bash
# Rebuild the Token Factory Cookbook section from the upstream repo.
# (index.html — the ecosystem page — is generated once via build_index.py and committed.)
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv 2>/dev/null || true
./.venv/bin/pip -q install --upgrade pip >/dev/null
./.venv/bin/pip -q install nbconvert markdown pygments >/dev/null
rm -rf .cache/cookbook-src
git clone --depth 1 https://github.com/nebius/token-factory-cookbook .cache/cookbook-src
./.venv/bin/python build_cookbook.py
touch .nojekyll
echo "Build complete."
