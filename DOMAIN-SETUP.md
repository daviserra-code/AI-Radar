# Domain Setup Guide for AI-Radar

## Overview
Setting up proper domains with HTTPS for:
- **ai-radar.it** (main site)
- **llmonpremise.com** (OnPremise section)

## Prerequisites
- Server IP: `46.224.91.14`
- Domains registered in Aruba
- SSH access to Hetzner server

---

## Step 1: Update DNS Records in Aruba

Login to your Aruba domain management panel and configure DNS:

### For ai-radar.it:
```
Type    Name    Value           TTL
A       @       46.224.91.14    3600
A       www     46.224.91.14    3600
```

### For llmonpremise.com:
```
Type    Name    Value           TTL
A       @       46.224.91.14    3600
A       www     46.224.91.14    3600
```

**Remove any existing redirects or CNAME records** that might conflict.

**⏱️ Wait 5-30 minutes for DNS propagation** before proceeding.

---

## Step 2: Verify DNS Propagation

From your local machine, check if DNS is working:

```powershell
nslookup ai-radar.it
nslookup www.ai-radar.it
nslookup llmonpremise.com
nslookup www.llmonpremise.com
```

All should return: `46.224.91.14`

---

## Step 3: Setup Nginx and SSL on Server

SSH to your server and run the setup script:

```bash
ssh root@46.224.91.14
cd /opt/ai-radar
chmod +x setup-domains.sh
./setup-domains.sh
```

This will:
- ✅ Install Nginx and Certbot
- ✅ Configure reverse proxy for both domains
- ✅ Setup HTTP to HTTPS redirects
- ✅ Configure security headers

---

## Step 4: Obtain SSL Certificates

After DNS propagation (verify with nslookup first!):

```bash
# For ai-radar.it
sudo certbot --nginx -d ai-radar.it -d www.ai-radar.it

# For llmonpremise.com
sudo certbot --nginx -d llmonpremise.com -d www.llmonpremise.com
```

**Important:** 
- Enter your email when prompted
- Agree to Terms of Service
- Choose option 2 to redirect HTTP to HTTPS

---

## Step 5: Update Application Configuration

Update docker-compose.yml environment variables:

```yaml
environment:
  DOMAIN: ai-radar.it
  ALLOWED_ORIGINS: https://ai-radar.it,https://www.ai-radar.it,https://llmonpremise.com,https://www.llmonpremise.com
  FORCE_HTTPS: true
```

Then restart the app:

```bash
cd /opt/ai-radar
docker compose restart app
```

---

## Step 6: Test Everything

### Test ai-radar.it:
- http://ai-radar.it → should redirect to https://ai-radar.it ✅
- http://www.ai-radar.it → should redirect to https://ai-radar.it ✅
- https://ai-radar.it → should load site ✅

### Test llmonpremise.com:
- http://llmonpremise.com → should redirect to https://llmonpremise.com ✅
- http://www.llmonpremise.com → should redirect to https://llmonpremise.com ✅
- https://llmonpremise.com → should load OnPremise section ✅

### Test SSL:
Visit: https://www.ssllabs.com/ssltest/analyze.html?d=ai-radar.it

---

## Step 7: Setup Auto-Renewal

Certbot automatically installs a cron job, but verify it works:

```bash
sudo certbot renew --dry-run
```

You should see: "Congratulations, all simulated renewals succeeded"

---

## Troubleshooting

### DNS not propagating?
```bash
# Check if server can resolve
dig ai-radar.it
dig llmonpremise.com
```

### Nginx errors?
```bash
# Check Nginx status
sudo systemctl status nginx

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

### SSL certificate fails?
Make sure:
1. DNS is fully propagated (wait longer)
2. Port 80 and 443 are open in firewall
3. Nginx is running

```bash
# Check firewall
sudo ufw status
sudo ufw allow 'Nginx Full'
```

### Application not loading?
```bash
# Check app is running
docker compose ps

# Check app logs
docker compose logs app --tail=50
```

---

## Maintenance

### Renew certificates manually:
```bash
sudo certbot renew
```

### Update Nginx config:
```bash
sudo nano /etc/nginx/sites-available/ai-radar
sudo nginx -t
sudo systemctl reload nginx
```

### Check certificate expiry:
```bash
sudo certbot certificates
```

---

## Quick Reference Commands

```bash
# Restart everything
sudo systemctl restart nginx
docker compose restart app

# View logs
sudo tail -f /var/log/nginx/access.log
docker compose logs app -f

# Force SSL renewal
sudo certbot renew --force-renewal
```

---

## Current Setup Summary

- **Main domain**: https://ai-radar.it (AI news portal)
- **Secondary domain**: https://llmonpremise.com (OnPremise guides)
- **Server**: Hetzner 46.224.91.14
- **Web server**: Nginx (reverse proxy)
- **SSL**: Let's Encrypt (auto-renews every 90 days)
- **App**: Docker container on port 8000
