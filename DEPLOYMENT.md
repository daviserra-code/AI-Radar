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
ssh root@46.224.91.14

# Navigate to project
cd /opt/AI-Radar

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
ssh root@46.224.91.14 "cd /opt/AI-Radar && ./deploy.sh"
```

**One-liner deploy from local:**
```powershell
git add -A; git commit -m "Deploy update"; git push; ssh root@46.224.91.14 "cd /opt/AI-Radar && ./deploy.sh"
```

### 4. Manual Deployment Steps (if script fails)

```bash
# On Hetzner server
cd /opt/AI-Radar
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

# Health check
curl http://localhost:8000/health | jq

# Detailed metrics
curl http://localhost:8000/api/metrics | jq

# Database backup
docker exec llmobs_db pg_dump -U llmobs_user -d llmobs_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 5.1. Database Backup & Restore

**Automated backup script** (`/opt/scripts/backup-ai-radar.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/ai-radar"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
docker exec llmobs_db pg_dump -U llmobs_user llmobs_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
echo "Backup completed: db_$DATE.sql.gz"
```

**Setup automated backups:**
```bash
chmod +x /opt/scripts/backup-ai-radar.sh
crontab -e
# Add: 0 2 * * * /opt/scripts/backup-ai-radar.sh >> /var/log/ai-radar-backup.log 2>&1
```

**Restore from backup:**
```bash
docker-compose stop app
gunzip -c /opt/backups/ai-radar/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i llmobs_db psql -U llmobs_user -d llmobs_db
docker-compose start app
```

### 6. Production Environment Configuration

**Create `.env` file on server** (CRITICAL for production):

```bash
# On Hetzner server
cd /opt/AI-Radar
cp .env.example .env
nano .env
```

**Required Production Settings:**

```env
# Database - Use strong password!
POSTGRES_USER=llmobs_user
POSTGRES_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD
POSTGRES_DB=llmobs_db
DATABASE_URL=postgresql+psycopg2://llmobs_user:STRONG_PASSWORD@db:5432/llmobs_db

# Security - GENERATE THESE!
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=YOUR_GENERATED_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
ENVIRONMENT=production
DOMAIN=46.224.91.14
ALLOWED_ORIGINS=http://46.224.91.14:8000,https://46.224.91.14:8000
FORCE_HTTPS=false  # Set to true after SSL setup

# Ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:latest

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Rate Limiting (adjust for production traffic)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000

# Scheduler
FETCH_INTERVAL_MINUTES=5
ARTICLES_PER_FEED=5
```

**Generate secure secrets:**
```bash
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
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
