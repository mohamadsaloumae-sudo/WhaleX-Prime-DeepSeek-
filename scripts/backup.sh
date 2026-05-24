#!/bin/bash

# Database backup script
BACKUP_DIR="/backups/whalex"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec whalex_postgres pg_dump -U whalex whalex_prime > "$BACKUP_DIR/whalex_db_$DATE.sql"

# Backup Redis
docker exec whalex_redis redis-cli --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Compress
gzip "$BACKUP_DIR/whalex_db_$DATE.sql"
gzip "$BACKUP_DIR/redis_$DATE.rdb"

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"