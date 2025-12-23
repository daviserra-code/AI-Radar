#!/bin/bash
# Domain Setup Script for AI-Radar with HTTPS
# Domains: ai-radar.it and llmonpremise.com

set -e

echo "🌐 Setting up domains with HTTPS for AI-Radar..."

# Install Nginx and Certbot
echo "📦 Installing Nginx and Certbot..."
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

# Create Nginx configuration for AI-Radar
echo "⚙️  Creating Nginx configuration..."
cat > /etc/nginx/sites-available/ai-radar <<'EOF'
# Redirect www to non-www for ai-radar.it
server {
    listen 80;
    server_name www.ai-radar.it;
    return 301 https://ai-radar.it$request_uri;
}

# Main ai-radar.it
server {
    listen 80;
    server_name ai-radar.it;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ai-radar.it;
    
    # SSL certificates (will be added by certbot)
    # ssl_certificate /etc/letsencrypt/live/ai-radar.it/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/ai-radar.it/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to FastAPI app
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /opt/ai-radar/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Create Nginx configuration for LLMOnPremise
cat > /etc/nginx/sites-available/llmonpremise <<'EOF'
# Redirect www to non-www for llmonpremise.com
server {
    listen 80;
    server_name www.llmonpremise.com;
    return 301 https://llmonpremise.com$request_uri;
}

# Main llmonpremise.com
server {
    listen 80;
    server_name llmonpremise.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name llmonpremise.com;
    
    # SSL certificates (will be added by certbot)
    # ssl_certificate /etc/letsencrypt/live/llmonpremise.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/llmonpremise.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to OnPremise section
    location / {
        proxy_pass http://localhost:8000/onpremise;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Static files
    location /static/ {
        alias /opt/ai-radar/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable sites
ln -sf /etc/nginx/sites-available/ai-radar /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/llmonpremise /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
nginx -t

# Restart Nginx
echo "🔄 Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx

echo ""
echo "✅ Nginx configured successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Update DNS records in Aruba:"
echo "   - ai-radar.it A record → 46.224.91.14"
echo "   - www.ai-radar.it A record → 46.224.91.14"
echo "   - llmonpremise.com A record → 46.224.91.14"
echo "   - www.llmonpremise.com A record → 46.224.91.14"
echo ""
echo "2. Wait for DNS propagation (5-30 minutes)"
echo ""
echo "3. Run SSL certificate setup:"
echo "   sudo certbot --nginx -d ai-radar.it -d www.ai-radar.it"
echo "   sudo certbot --nginx -d llmonpremise.com -d www.llmonpremise.com"
echo ""
echo "4. Test auto-renewal:"
echo "   sudo certbot renew --dry-run"
echo ""
