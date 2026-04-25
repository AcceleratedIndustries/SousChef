#!/usr/bin/env bash
# Build the two release artifacts:
#   dist/souschef.mcpb        -- Claude Desktop extension (MCP server)
#   dist/souschef-skill.zip   -- Claude Desktop skill (uploaded via Customize > Skills)
#
# Requires:
#   - mcpb CLI       (npm install -g @anthropic-ai/mcpb)
#   - zip
#
# Usage: scripts/build-release.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
mkdir -p "$DIST"

echo "==> Building souschef.mcpb"
if ! command -v mcpb >/dev/null 2>&1; then
  echo "error: mcpb CLI not found. Install with: npm install -g @anthropic-ai/mcpb" >&2
  exit 1
fi

# mcpb pack reads manifest.json + .mcpbignore from the project root and
# produces a single .mcpb file. The "uv" runtime means deps come from
# pyproject.toml -- we don't bundle them.
( cd "$ROOT" && mcpb pack . "$DIST/souschef.mcpb" )

echo "==> Building souschef-skill.zip"
# Claude Desktop expects the skill folder as the ZIP root (not a parent).
# We zip from skills/ so the archive contains "souschef/SKILL.md" at the top.
rm -f "$DIST/souschef-skill.zip"
( cd "$ROOT/skills" && zip -r "$DIST/souschef-skill.zip" souschef -x '*.DS_Store' )

echo
echo "Built:"
ls -lh "$DIST/souschef.mcpb" "$DIST/souschef-skill.zip"
