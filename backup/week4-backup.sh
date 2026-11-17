#!/bin/bash
set -u
SOURCE="/var/www/html/"
DEST="backupsvc@100.68.196.69"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP="/srv/backups/viikko4/website-$DATE"
LOG="/home/ubuntu/week4-backup.log"
KEY="/home/ubuntu/.ssh/id_ed25519_week4_backup"

if rsync -av --mkpath -e "ssh -i $KEY -o BatchMode=yes -o IdentitiesOnly=yes" "$SOURCE" "$DEST:$BACKUP/"; then
  echo "$(date): Backup SUCCESS - $BACKUP" >> "$LOG"
  echo "Backup completed successfully!"
else
  echo "$(date): Backup FAILED - $BACKUP" >> "$LOG"
  echo "Backup failed!" >&2
  exit 1
fi
