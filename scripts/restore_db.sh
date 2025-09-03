#!/bin/bash
set -e

# Database restore script for secure-auth-service
# This script restores database from backup files

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
DB_NAME="${POSTGRES_DB:-authdb}"
DB_USER="${POSTGRES_USER:-authuser}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

# Function to show usage
usage() {
    echo "Usage: $0 <backup_file>"
    echo "       $0 --latest"
    echo "       $0 --list"
    echo ""
    echo "Options:"
    echo "  <backup_file>  Path to backup file (.sql.gz or .sql.custom.gz)"
    echo "  --latest       Restore from latest backup"
    echo "  --list         List available backups"
    echo ""
    echo "Environment variables:"
    echo "  BACKUP_DIR     Backup directory (default: /app/backups)"
    echo "  POSTGRES_DB    Database name (default: authdb)"
    echo "  POSTGRES_USER  Database user (default: authuser)"
    echo "  DB_HOST        Database host (default: db)"
    echo "  DB_PORT        Database port (default: 5432)"
}

# Function to list backups
list_backups() {
    echo "Available backups in $BACKUP_DIR:"
    if ls "$BACKUP_DIR"/${DB_NAME}_backup_*.gz >/dev/null 2>&1; then
        ls -la "$BACKUP_DIR"/${DB_NAME}_backup_*.gz
    else
        echo "No backups found."
        exit 1
    fi
}

# Function to get latest backup
get_latest_backup() {
    LATEST=$(ls -t "$BACKUP_DIR"/${DB_NAME}_backup_*.sql.gz 2>/dev/null | head -1 || echo "")
    if [ -z "$LATEST" ]; then
        # Try custom format
        LATEST=$(ls -t "$BACKUP_DIR"/${DB_NAME}_backup_*.sql.custom.gz 2>/dev/null | head -1 || echo "")
    fi
    
    if [ -z "$LATEST" ]; then
        echo "No backup files found in $BACKUP_DIR"
        exit 1
    fi
    
    echo "$LATEST"
}

# Function to restore database
restore_database() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        echo "Error: Backup file not found: $backup_file"
        exit 1
    fi
    
    echo "Restoring database from: $backup_file"
    echo "Database: $DB_NAME"
    echo "Host: $DB_HOST:$DB_PORT"
    echo "User: $DB_USER"
    
    # Confirm before proceeding
    read -p "This will REPLACE all data in database '$DB_NAME'. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restore cancelled."
        exit 1
    fi
    
    # Create temporary file for decompressed backup
    TEMP_FILE=$(mktemp)
    trap "rm -f $TEMP_FILE" EXIT
    
    # Decompress backup
    echo "Decompressing backup..."
    if [[ "$backup_file" == *.custom.gz ]]; then
        gunzip -c "$backup_file" > "$TEMP_FILE"
        RESTORE_FORMAT="custom"
    else
        gunzip -c "$backup_file" > "$TEMP_FILE"
        RESTORE_FORMAT="plain"
    fi
    
    # Drop existing database connections
    echo "Terminating existing connections..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();" || true
    
    # Drop and recreate database
    echo "Dropping database..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS $DB_NAME;"
    
    echo "Creating database..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        -c "CREATE DATABASE $DB_NAME;"
    
    # Restore database
    echo "Restoring data..."
    if [ "$RESTORE_FORMAT" = "custom" ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --no-password \
            "$TEMP_FILE"
    else
        PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            -f "$TEMP_FILE"
    fi
    
    echo "Database restore completed successfully!"
    echo "Don't forget to run migrations if needed: alembic upgrade head"
}

# Main script
case "$1" in
    --list)
        list_backups
        ;;
    --latest)
        BACKUP_FILE=$(get_latest_backup)
        echo "Latest backup: $BACKUP_FILE"
        restore_database "$BACKUP_FILE"
        ;;
    --help|-h)
        usage
        ;;
    "")
        usage
        exit 1
        ;;
    *)
        restore_database "$1"
        ;;
esac
