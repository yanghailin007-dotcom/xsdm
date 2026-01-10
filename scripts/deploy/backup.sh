#!/bin/bash

# 备份脚本 - 备份数据库和配置文件
# 使用方法: bash backup.sh

set -e

echo "========================================"
echo "   数据备份脚本"
echo "========================================"
echo ""

# 配置
APP_USER=${APP_USER:-novelapp}
PROJECT_DIR="/home/$APP_USER/novel-system"
BACKUP_DIR="/home/$APP_USER/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 创建备份目录
mkdir -p $BACKUP_DIR

echo -e "${YELLOW}备份目录: $BACKUP_DIR${NC}"
echo ""

# 备份数据库
echo -e "${YELLOW}步骤 1/3: 备份数据库${NC}"
if [ -d "$PROJECT_DIR/data" ]; then
    find $PROJECT_DIR/data -name "*.db" -type f -exec cp {} $BACKUP_DIR/db_$DATE.db \; 2>/dev/null
    if [ -f "$BACKUP_DIR/db_$DATE.db" ]; then
        echo -e "${GREEN}✓ 数据库备份完成: db_$DATE.db${NC}"
    else
        echo -e "${YELLOW}未找到数据库文件${NC}"
    fi
else
    echo -e "${YELLOW}数据目录不存在${NC}"
fi
echo ""

# 备份配置文件
echo -e "${YELLOW}步骤 2/3: 备份配置文件${NC}"
if [ -f "$PROJECT_DIR/.env" ]; then
    cp $PROJECT_DIR/.env $BACKUP_DIR/env_$DATE.bak
    echo -e "${GREEN}✓ 配置文件备份完成: env_$DATE.bak${NC}"
else
    echo -e "${YELLOW}.env文件不存在${NC}"
fi
echo ""

# 备份项目文件（可选）
echo -e "${YELLOW}步骤 3/3: 备份项目文件${NC}"
read -p "是否备份项目文件？(y/n): " BACKUP_PROJECT
if [ "$BACKUP_PROJECT" = "y" ] || [ "$BACKUP_PROJECT" = "Y" ]; then
    tar -czf $BACKUP_DIR/project_$DATE.tar.gz \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='logs/*' \
        --exclude='temp_fanqie_upload/*' \
        -C $PROJECT_DIR .
    echo -e "${GREEN}✓ 项目文件备份完成: project_$DATE.tar.gz${NC}"
fi
echo ""

# 清理旧备份（保留最近30天）
echo -e "${YELLOW}清理旧备份...${NC}"
find $BACKUP_DIR -type f -mtime +30 -delete
echo -e "${GREEN}✓ 旧备份清理完成${NC}"
echo ""

echo "========================================"
echo -e "${GREEN}✓ 备份完成！${NC}"
echo "========================================"
echo ""
echo "备份文件列表:"
ls -lh $BACKUP_DIR/
echo ""