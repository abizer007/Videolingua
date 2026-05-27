# Export VidioLingua system architecture diagram to PNG and SVG.
# Requires: Node.js, npx (run from project root).

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $Root

Write-Host "Exporting architecture diagram from docs/architecture.mmd ..."
npx --yes @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.png
npx --yes @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.svg
Write-Host "Done. Output: docs/architecture.png, docs/architecture.svg"
