# Quick Deploy (no commit message prompt)
# Usage: powershell -ExecutionPolicy Bypass -File .\quick-deploy.ps1
# Or just: .\quick-deploy.ps1 (if SSH keys are set up)

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\deploy-to-hetzner.ps1" "Quick deploy: $timestamp"
