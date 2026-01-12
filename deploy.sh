#!/bin/bash
set -e

# Configuration
VPS_HOST="barsik.online"
VPS_USER="root"
VPS_PATH="/var/www/firehorse"
LOCAL_PATH="/srv/firehorse-backend"

echo "🚀 Starting production deploy to $VPS_HOST"

# 1. Build frontend
echo "📦 Building frontend..."
cd $LOCAL_PATH/frontend
VITE_API_URL=/api npm run build

# 2. Sync files to VPS
echo "📤 Syncing files to VPS..."
rsync -avz --delete \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.env*' \
  --exclude='*.log' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  $LOCAL_PATH/ $VPS_USER@$VPS_HOST:$VPS_PATH/

# 3. Copy production nginx config
echo "🔧 Configuring nginx..."
scp $LOCAL_PATH/nginx.conf $VPS_USER@$VPS_HOST:/etc/nginx/sites-available/firehorse
ssh $VPS_USER@$VPS_HOST "ln -sf /etc/nginx/sites-available/firehorse /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx"

# 4. Restart services
echo "🔄 Restarting services..."
ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && docker-compose down && docker-compose up -d"

echo "✅ Deploy complete! Visit https://$VPS_HOST"
