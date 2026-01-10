#!/bin/bash
# 智能部署脚本 - 只同步必要的代码，跳过大文件

# 配置变量
SERVER_IP="8.163.37.124"
SERVER_USER="novelapp"
SERVER_PATH="/home/novelapp/novel-system"
LOCAL_PATH="d:/work6.05"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  智能部署脚本 - 快速同步必要代码${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查rsync是否安装
if ! command -v rsync &> /dev/null; then
    echo -e "${RED}错误: 未找到 rsync 命令${NC}"
    echo "请安装 rsync: apt install rsync (Linux) 或 choco install rsync (Windows)"
    exit 1
fi

# 显示将要同步的内容
echo -e "\n${YELLOW}将要同步的目录:${NC}"
echo "  ✓ src/        - 核心代码"
echo "  ✓ web/        - Web界面"
echo "  ✓ config/     - 配置文件"
echo "  ✓ scripts/    - 脚本工具"
echo "  ✓ requirements.txt - 依赖列表"
echo "  ✓ web/        - 模板和静态文件"
echo ""
echo -e "${YELLOW}排除的内容 (不同步):${NC}"
echo "  ✗ Chrome/     - 浏览器自动化 (1.6GB)"
echo "  ✗ .git/       - Git历史 (605MB)"
echo "  ✗ .venv/      - 虚拟环境 (15MB)"
echo "  ✗ generated_images/ - 生成的图片 (39MB)"
echo "  ✗ 小说项目/    - 本地项目数据"
echo "  ✗ logs/       - 日志文件"
echo "  ✗ temp_fanqie_upload/ - 临时文件"
echo "  ✗ __pycache__/ - Python缓存"
echo "  ✗ *.pyc       - 编译文件"
echo ""

# 确认
read -p "确认开始同步? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消部署"
    exit 0
fi

echo -e "\n${GREEN}开始同步...${NC}"

# 使用rsync同步，只传输必要的文件
rsync -avz --progress \
    --exclude='Chrome/' \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='venv/' \
    --exclude='generated_images/' \
    --exclude='logs/' \
    --exclude='temp_fanqie_upload/' \
    --exclude='chapter_failures/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.env' \
    --exclude='*.db' \
    --exclude='小说项目/' \
    --exclude='test_*.py' \
    --exclude='check_*.py' \
    --exclude='diagnose_*.py' \
    --exclude='debug_*.py' \
    --exclude='*.tar.gz' \
    --exclude='.vscode/' \
    --exclude='.idea/' \
    --exclude='node_modules/' \
    --exclude='data/users.db' \
    --exclude='*.log' \
    --exclude='.claude/' \
    --exclude='*.pem' \
    --exclude='*.key' \
    --exclude='id_rsa*' \
    --exclude='Chrome.rar' \
    --delete \
    -e "ssh -i d:/work6.05/xsdm.pem -o StrictHostKeyChecking=no" \
    "$LOCAL_PATH/" \
    "${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/"

# 检查同步结果
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ 同步完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\n${YELLOW}下一步操作:${NC}"
    echo "1. SSH连接到服务器:"
    echo "   ssh -i d:/work6.05/xsdm.pem ${SERVER_USER}@${SERVER_IP}"
    echo ""
    echo "2. 进入项目目录:"
    echo "   cd ${SERVER_PATH}"
    echo ""
    echo "3. 创建虚拟环境并安装依赖:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "4. 配置环境变量:"
    echo "   cp .env.example .env"
    echo "   vim .env"
    echo ""
    echo "5. 重启服务:"
    echo "   sudo supervisorctl restart novel-system"
    echo ""
else
    echo -e "\n${RED}✗ 同步失败，请检查错误信息${NC}"
    exit 1
fi