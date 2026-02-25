#!/bin/bash

# 配置
BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME=${POSTGRES_DB:-paper_reader}
DB_USER=${POSTGRES_USER:-paperuser}

mkdir -p $BACKUP_DIR

echo "Starting database backup: $DB_NAME..."

# 执行备份
pg_dump -h postgres -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$TIMESTAMP.sql

# 压缩
gzip $BACKUP_DIR/db_backup_$TIMESTAMP.sql

# 保留最近 7 天的备份
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# 实际生产中这里还可以加入上传到 S3/MinIO 的逻辑
# mc cp $BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz myminio/backups/
