#!/bin/bash
set -e

# Database backup script for secure-auth-service
# This script creates database backups with rotation

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
DB_NAME="${POSTGRES_DB:-authdb}"
DB_USER="${POSTGRES_USER:-authuser}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_$TIMESTAMP.sql"

echo "Starting database backup..."
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo "Backup file: $BACKUP_FILE"

# Create database backup
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --no-password \
    --format=custom \
    --blobs \
    --file="$BACKUP_FILE.custom"

# Also create plain SQL backup for readability
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --no-password \
    --format=plain \
    --file="$BACKUP_FILE"

# Compress backups
gzip "$BACKUP_FILE"
gzip "$BACKUP_FILE.custom"

echo "Backup completed: $BACKUP_FILE.gz"
echo "Custom backup: $BACKUP_FILE.custom.gz"

# Clean up old backups
if [ "$RETENTION_DAYS" -gt 0 ]; then
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.sql.custom.gz" -mtime +$RETENTION_DAYS -delete
    echo "Cleanup completed."
fi

# List current backups
echo "Current backups:"
ls -la "$BACKUP_DIR"/${DB_NAME}_backup_*.gz | tail -5

echo "Database backup completed successfully!"
