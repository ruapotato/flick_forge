#!/bin/bash
# Flick Forge Deployment Script for 255.one
# AGPL-3.0 License

set -e

SERVER="255"
DOMAIN="255.one"
APP_DIR="/opt/flick_forge"
USER="flick"

echo "=== Flick Forge Deployment Script ==="
echo "Target: $DOMAIN"
echo ""

# Check if we're running the setup or deploy phase
case "${1:-deploy}" in
    setup)
        echo "=== Phase 1: Server Setup ==="

        # Install required packages
        ssh $SERVER << 'SETUP_EOF'
set -e
echo "[*] Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    nginx \
    postgresql \
    postgresql-contrib \
    python3-venv \
    python3-pip \
    certbot \
    python3-certbot-nginx \
    git

echo "[*] Creating flick user..."
sudo useradd -r -m -s /bin/bash flick 2>/dev/null || echo "User already exists"

echo "[*] Creating application directory..."
sudo mkdir -p /opt/flick_forge
sudo chown flick:flick /opt/flick_forge

echo "[*] Setting up PostgreSQL..."
sudo -u postgres psql -c "CREATE USER flick WITH PASSWORD 'CHANGEME_SECURE_PASSWORD';" 2>/dev/null || echo "User exists"
sudo -u postgres psql -c "CREATE DATABASE flick_store OWNER flick;" 2>/dev/null || echo "Database exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE flick_store TO flick;"

echo "[*] Creating systemd service..."
sudo tee /etc/systemd/system/flick_forge.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Flick Forge - AI App Store Backend
After=network.target postgresql.service

[Service]
User=flick
Group=flick
WorkingDirectory=/opt/flick_forge
Environment="PATH=/opt/flick_forge/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/opt/flick_forge/venv/bin/gunicorn --workers 4 --bind unix:/opt/flick_forge/flick_forge.sock app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "[*] Setting up nginx configuration..."
sudo tee /etc/nginx/sites-available/flick_forge > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name 255.one;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 256;

    location / {
        proxy_pass http://unix:/opt/flick_forge/flick_forge.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    location /static {
        alias /opt/flick_forge/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Package downloads
    location /packages {
        alias /opt/flick_forge/packages;
        expires 7d;
    }

    # API rate limiting
    location /api {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://unix:/opt/flick_forge/flick_forge.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINX_EOF

# Add rate limiting to nginx.conf
sudo grep -q "limit_req_zone" /etc/nginx/nginx.conf || sudo sed -i '/http {/a \    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;' /etc/nginx/nginx.conf

sudo ln -sf /etc/nginx/sites-available/flick_forge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl reload nginx

echo "[*] Server setup complete!"
SETUP_EOF
        ;;

    deploy)
        echo "=== Phase 2: Deploy Application ==="

        echo "[*] Syncing files to server..."
        rsync -avz --delete \
            --exclude '__pycache__' \
            --exclude '*.pyc' \
            --exclude 'venv' \
            --exclude '.git' \
            --exclude '.env' \
            --exclude 'instance' \
            ./ $SERVER:/opt/flick_forge/

        ssh $SERVER << 'DEPLOY_EOF'
set -e
cd /opt/flick_forge

echo "[*] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[*] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

echo "[*] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    # Generate a secure secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
    echo "[!] Please update .env with your database password and other settings"
fi

echo "[*] Creating packages directory..."
mkdir -p packages

echo "[*] Setting permissions..."
sudo chown -R flick:flick /opt/flick_forge
chmod -R 644 /opt/flick_forge/static/css/* /opt/flick_forge/static/js/* 2>/dev/null || true

echo "[*] Restarting service..."
sudo systemctl daemon-reload
sudo systemctl enable flick_forge
sudo systemctl restart flick_forge

echo "[*] Checking service status..."
sleep 2
sudo systemctl status flick_forge --no-pager

echo "[*] Deployment complete!"
DEPLOY_EOF
        ;;

    ssl)
        echo "=== Phase 3: Setup SSL ==="
        ssh $SERVER << 'SSL_EOF'
set -e
echo "[*] Obtaining SSL certificate..."
sudo certbot --nginx -d 255.one --non-interactive --agree-tos -m admin@255.one
echo "[*] SSL setup complete!"
SSL_EOF
        ;;

    logs)
        echo "=== Viewing logs ==="
        ssh $SERVER "sudo journalctl -u flick_forge -f"
        ;;

    status)
        echo "=== Service Status ==="
        ssh $SERVER "sudo systemctl status flick_forge --no-pager && echo '' && curl -s --unix-socket /opt/flick_forge/flick_forge.sock http://localhost/ | head -20"
        ;;

    init-db)
        echo "=== Initialize Database ==="
        ssh $SERVER << 'INITDB_EOF'
set -e
cd /opt/flick_forge
source venv/bin/activate

echo "[*] Running database migrations..."
python3 -c "
from app import app
from models import db, User, UserTier
import os

with app.app_context():
    db.create_all()
    print('[*] Database tables created')

    # Create admin user if not exists
    admin = User.query.filter_by(tier=UserTier.ADMIN.value).first()
    if not admin:
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@255.one')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'ChangeMe123!')

        admin = User(
            username=admin_username,
            email=admin_email,
            tier=UserTier.ADMIN.value,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f'[*] Created admin user: {admin_username}')
        print('[!] IMPORTANT: Change the admin password!')
    else:
        print('[*] Admin user already exists')
"
echo "[*] Database initialization complete!"
INITDB_EOF
        ;;

    setup-claude)
        echo "=== Setup Claude Code for AI App Building ==="
        ssh $SERVER << 'CLAUDE_EOF'
set -e
# Check if claude is available
if command -v claude &> /dev/null; then
    echo "[*] Claude Code is already installed: $(claude --version)"
else
    echo "[!] Claude Code not found. Please install it manually."
    echo "    Visit: https://claude.ai/download"
    exit 1
fi

# Create workspace for AI app building
sudo mkdir -p /opt/flick_forge/ai_workspace
sudo chown flick:flick /opt/flick_forge/ai_workspace

echo "[*] Claude Code setup complete!"
echo "[!] Make sure ANTHROPIC_API_KEY is set in the environment"
CLAUDE_EOF
        ;;

    full-install)
        echo "=== Full Installation ==="
        echo "[1/5] Setting up server..."
        $0 setup
        echo ""
        echo "[2/5] Deploying application..."
        $0 deploy
        echo ""
        echo "[3/5] Setting up SSL..."
        $0 ssl
        echo ""
        echo "[4/5] Initializing database..."
        $0 init-db
        echo ""
        echo "[5/5] Setting up Claude Code..."
        $0 setup-claude
        echo ""
        echo "=== Full installation complete! ==="
        echo "Site available at: https://$DOMAIN"
        ;;

    *)
        echo "Usage: $0 {setup|deploy|ssl|init-db|setup-claude|full-install|logs|status}"
        echo ""
        echo "  setup        - Install packages and configure server (run once)"
        echo "  deploy       - Deploy/update the application"
        echo "  ssl          - Setup Let's Encrypt SSL certificate"
        echo "  init-db      - Initialize database and create admin user"
        echo "  setup-claude - Setup Claude Code for AI app building"
        echo "  full-install - Run all setup steps (setup + deploy + ssl + init-db + setup-claude)"
        echo "  logs         - View application logs"
        echo "  status       - Check service status"
        exit 1
        ;;
esac

echo ""
echo "=== Done ==="
