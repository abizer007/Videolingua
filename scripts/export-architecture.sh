#!/usr/bin/env bash
# Export VidioLingua system architecture diagram to PNG and SVG.
# Requires: Node.js, npx (run from project root).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

echo "Exporting architecture diagram from docs/architecture.mmd ..."
npx --yes @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.png
npx --yes @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.svg
echo "Done. Output: docs/architecture.png, docs/architecture.svg"
