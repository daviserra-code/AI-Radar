# Deploy to Hetzner Server
# Usage: .\deploy-to-hetzner.ps1 "Your commit message"

param(
    [string]$CommitMessage = "Update deployment"
)

$SERVER_IP = "46.224.91.14"
$SERVER_USER = "root"
$PROJECT_PATH = "/opt/AI-Radar"

Write-Host "Starting deployment to Hetzner..." -ForegroundColor Cyan

# Step 1: Add all changes
Write-Host "`nAdding changes..." -ForegroundColor Yellow
git add -A

# Step 2: Commit
Write-Host "Committing changes..." -ForegroundColor Yellow
git commit -m $CommitMessage

# Step 3: Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "Git push failed!" -ForegroundColor Red
    exit 1
}

# Step 4: Deploy to server
Write-Host "`nDeploying to Hetzner server..." -ForegroundColor Yellow
$deployCommands = @"
cd $PROJECT_PATH && \
git pull origin main && \
chmod +x deploy.sh && \
./deploy.sh
"@

ssh "${SERVER_USER}@${SERVER_IP}" $deployCommands

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
    Write-Host "Application available at: http://${SERVER_IP}:8000" -ForegroundColor Cyan
} else {
    Write-Host "`nDeployment failed!" -ForegroundColor Red
    exit 1
}
