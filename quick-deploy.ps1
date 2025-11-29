# Quick Deploy (no commit message prompt)
# Usage: .\quick-deploy.ps1

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
.\deploy-to-hetzner.ps1 "Quick deploy: $timestamp"
