# AI-Radar Deployment Status

## ✅ Successfully Deployed

### Domain: ai-radar.it
- **HTTPS**: ✅ Working (Let's Encrypt SSL)
- **Certificate Expiry**: March 23, 2026 (89 days)
- **Nginx**: ✅ Configured and running
- **Application**: ✅ Running on Docker
- **Auto-renewal**: ✅ Configured (Certbot)

**Access URLs:**
- https://ai-radar.it
- https://www.ai-radar.it
- Both automatically redirect HTTP → HTTPS

## ⚠️ Pending Configuration

### Domain: llmonpremise.com
- **Issue**: DNS has multiple A records:
  - ❌ 62.149.128.40 (should be removed)
  - ✅ 46.224.91.14 (correct)
- **Status**: SSL certificate failed due to DNS conflict
- **Action Required**: Go to Aruba DNS settings and remove the 62.149.128.40 A record

**Steps to fix:**
1. Login to Aruba domain panel
2. Find llmonpremise.com DNS settings
3. Remove the A record pointing to 62.149.128.40
4. Keep only 46.224.91.14
5. Wait 5-30 minutes for DNS propagation
6. Run: `ssh root@46.224.91.14 "certbot --nginx -d llmonpremise.com -d www.llmonpremise.com --non-interactive --agree-tos --email admin@llmonpremise.com"`

## Server Configuration

**IP Address**: 46.224.91.14

**Nginx Configuration**:
- `/etc/nginx/sites-available/ai-radar` ✅
- `/etc/nginx/sites-available/llmonpremise` ⚠️ (waiting for DNS fix)
- Port 80: HTTP → HTTPS redirect
- Port 443: HTTPS with SSL termination
- Proxy to: localhost:8000

**Docker Services**:
- `llmobs_db`: PostgreSQL 16 on port 5433
- `llmobs_app`: FastAPI on port 8000
- Network: ainetwork

**SSL Certificates**:
- Provider: Let's Encrypt
- Auto-renewal: Enabled (certbot.timer)
- Check renewal: `sudo certbot renew --dry-run`

## Application Settings

**Environment**: production
**Primary Domain**: ai-radar.it
**Allowed Origins**:
- https://ai-radar.it
- https://www.ai-radar.it
- https://llmonpremise.com
- https://www.llmonpremise.com

**Security**:
- HTTPS enforced
- HSTS enabled
- Security headers configured
- Rate limiting active

## Recent Changes

1. ✅ Added Google AI Blog and Anthropic News RSS sources
2. ✅ Fixed authentication (Bearer token issue)
3. ✅ Fixed template context (user → current_user)
4. ✅ Created admin user (admin/admin123)
5. ✅ Configured Nginx reverse proxy
6. ✅ Obtained Let's Encrypt SSL certificate for ai-radar.it
7. ✅ Configured automatic certificate renewal

## Admin Access

**Login URL**: https://ai-radar.it/login
**Username**: admin
**Password**: admin123

After login, admin panel is visible in the top navigation bar.

## Monitoring & Maintenance

**Check application logs**:
```bash
ssh root@46.224.91.14 "cd /opt/ai-radar && docker compose logs -f app"
```

**Check Nginx logs**:
```bash
ssh root@46.224.91.14 "tail -f /var/log/nginx/access.log"
ssh root@46.224.91.14 "tail -f /var/log/nginx/error.log"
```

**Check SSL certificates**:
```bash
ssh root@46.224.91.14 "certbot certificates"
```

**Restart services**:
```bash
ssh root@46.224.91.14 "cd /opt/ai-radar && docker compose restart"
ssh root@46.224.91.14 "systemctl restart nginx"
```

## Next Steps

1. **Fix llmonpremise.com DNS** (remove duplicate A record)
2. **Test HTTPS on llmonpremise.com** after DNS fix
3. **Monitor certificate auto-renewal** (first renewal in ~60 days)
4. **Consider server reboot** for kernel update (optional, but recommended)
