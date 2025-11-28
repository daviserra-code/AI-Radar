# AI-Radar Deployment Guide

## Local to Hetzner Deployment Workflow

### 1. Local Development (Your Machine)

Make changes, test locally, then push to GitHub:

```powershell
# After making changes
git add -A
git commit -m "Your commit message"
git push origin main
```

### 2. Deploy to Hetzner Server

SSH into your Hetzner server and run the deployment script:

```bash
# SSH into server
ssh root@your-server-ip

# Navigate to project
cd /path/to/AI-Radar

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

The script will:
- Pull latest code from GitHub
- Stop current containers
- Rebuild Docker images
- Start fresh containers
- Show status and logs

### 3. Quick Deploy Commands

**From your local machine (PowerShell):**
```powershell
# Push changes to GitHub
git add -A; git commit -m "Update feature"; git push

# Deploy to server via SSH
ssh root@your-server-ip "cd /path/to/AI-Radar && ./deploy.sh"
```

**One-liner deploy from local:**
```powershell
git add -A; git commit -m "Deploy update"; git push; ssh root@your-server-ip "cd /path/to/AI-Radar && ./deploy.sh"
```

### 4. Manual Deployment Steps (if script fails)

```bash
# On Hetzner server
cd /path/to/AI-Radar
git pull origin main
docker-compose down
docker-compose up -d --build
docker-compose logs -f
```

### 5. Useful Server Commands

```bash
# Check running containers
docker ps

# View logs
docker-compose logs -f llmobs_app

# Restart specific service
docker-compose restart llmobs_app

# Check disk space
df -h

# Monitor resources
docker stats

# Database backup
docker exec llmobs_db pg_dump -U llmobs_user -d llmobs_db > backup_$(date +%Y%m%d).sql
```

### 6. Environment Configuration

Ensure your server has a `.env` file or environment variables set in `docker-compose.yml`:

```yaml
environment:
  DATABASE_URL: postgresql+psycopg2://llmobs_user:llmobs_pass@db:5432/llmobs_db
  OLLAMA_HOST: http://ollama:11434
  OLLAMA_MODEL: llama3.2:latest
  INGEST_INTERVAL_MINUTES: "5"
```

### 7. Nginx Reverse Proxy (Optional)

If you want to expose the app on port 80/443:

```nginx
# /etc/nginx/sites-available/ai-radar
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 8. SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 9. Troubleshooting

**Container won't start:**
```bash
docker-compose logs llmobs_app
docker-compose down
docker system prune -a
docker-compose up -d --build
```

**Database issues:**
```bash
docker exec -it llmobs_db psql -U llmobs_user -d llmobs_db
# Run SQL commands to check tables
```

**Ollama not responding:**
```bash
docker logs ollama
docker restart ollama
docker network inspect ainetwork
```

### 10. Monitoring

**Set up log rotation:**
```bash
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

**System resources:**
```bash
# Check memory
free -h

# Check CPU
top

# Check Docker usage
docker system df
```
