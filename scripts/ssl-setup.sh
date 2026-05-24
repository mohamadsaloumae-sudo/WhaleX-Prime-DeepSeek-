#!/bin/bash

# SSL Certificate setup for Plesk (Hunters Germany)
DOMAIN="whalexapp.io"
EMAIL="admin@whalexapp.io"

# Install certbot
apt-get update
apt-get install -y certbot

# Obtain certificate
certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN -d api.$DOMAIN --non-interactive --agree-tos -m $EMAIL

# Copy to nginx ssl directory
mkdir -p ../nginx/ssl
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ../nginx/ssl/cert.pem
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ../nginx/ssl/key.pem

# Set up auto-renewal
echo "0 0 1 * * certbot renew --quiet --post-hook 'docker restart whalex_nginx'" | crontab -

echo "SSL configured for $DOMAIN"