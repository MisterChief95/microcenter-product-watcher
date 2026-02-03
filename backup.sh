#!/bin/bash
# Simple backup script for the SQLite database

BACKUP_DIR="./backups"
DB_FILE="./data/products.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/products_${TIMESTAMP}.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file not found at $DB_FILE"
    exit 1
fi

# Create backup
cp "$DB_FILE" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup created successfully: $BACKUP_FILE"

    # Optional: Keep only last 7 backups
    cd "$BACKUP_DIR"
    ls -t products_*.db | tail -n +8 | xargs -r rm
    echo "Cleaned up old backups (keeping last 7)"
else
    echo "Error: Backup failed"
    exit 1
fi
