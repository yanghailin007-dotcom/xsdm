#!/bin/bash
# SSL证书申请问题诊断脚本
# 使用方法: sudo bash diagnose_ssl_issue.sh

echo "========================================"
echo "  SSL证书申请问题诊断工具"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "🔍 步骤1: 检查服务器公网IP"
echo "----------------------------------------"
PUBLIC_IP=$(curl -s ifconfig.me)
echo "服务器公网IP: $PUBLIC_IP"
echo ""

echo "🔍 步骤2: 检查Nginx状态"
echo "----------------------------------------"
if systemctl is-active --quiet nginx; then
    check_pass "Nginx正在运行"
else
    check_fail "Nginx未运行，尝试启动..."
    systemctl start nginx
    if systemctl is-active --quiet nginx; then
        check_pass "Nginx已启动"
    else
        check_fail "Nginx启动失败"
    fi
fi
echo ""

echo "🔍 步骤3: 检查端口监听"
echo "----------------------------------------"
if netstat -tlnp | grep -q ":80 "; then
    check_pass "80端口正在监听"
    netstat -tlnp | grep ":80 "
else
    check_fail "80端口未监听"
fi

if netstat -tlnp | grep -q ":443 "; then
    check_pass "443端口正在监听"
else
    check_warn "443端口未监听（SSL证书申请后会监听）"
fi
echo ""

echo "🔍 步骤4: 检查防火墙状态"
echo "----------------------------------------"
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        check_pass "UFW防火墙已启用"
        echo "当前UFW规则："
        ufw status numbered
    else
        check_warn "UFW防火墙未启用"
    fi
else
    check_warn "未检测到UFW防火墙"
fi
echo ""

echo "🔍 步骤5: 检查Nginx配置"
echo "----------------------------------------"
if nginx -t 2>&1 | grep -q "successful"; then
    check_pass "Nginx配置文件语法正确"
else
    check_fail "Nginx配置文件有错误"
    nginx -t
fi
echo ""

echo "🔍 步骤6: 检查域名解析（需要手动验证）"
echo "----------------------------------------"
echo "请在本地电脑执行以下命令验证DNS解析："
echo ""
echo "  nslookup xsdm.com.cn"
echo "  nslookup www.xsdm.com.cn"
echo ""
echo "预期结果：应该解析到 $PUBLIC_IP"
echo ""

echo "🔍 步骤7: 测试HTTP访问（需要从外网测试）"
echo "----------------------------------------"
echo "请在本地电脑执行以下命令："
echo ""
echo "  curl -I http://xsdm.com.cn"
echo "  curl -I http://www.xsdm.com.cn"
echo ""
echo "预期结果：应该返回HTTP 200或其他HTTP状态码"
echo ""

echo "========================================"
echo "  诊断总结"
echo "========================================"
echo ""
echo "服务器公网IP: $PUBLIC_IP"
echo ""
echo "📋 下一步操作："
echo ""
echo "1. 确认DNS解析配置："
echo "   - 登录阿里云DNS控制台: https://dns.console.aliyun.com/"
echo "   - 确保A记录指向: $PUBLIC_IP"
echo ""
echo "2. 配置阿里云安全组："
echo "   - 登录阿里云ECS控制台"
echo "   - 添加入方向规则：端口80、443，授权对象0.0.0.0/0"
echo ""
echo "3. 配置服务器防火墙："
if command -v ufw &> /dev/null; then
    echo "   sudo ufw allow 80/tcp"
    echo "   sudo ufw allow 443/tcp"
fi
echo ""
echo "4. 等待DNS生效（10-30分钟）"
echo ""
echo "5. 验证DNS解析："
echo "   nslookup xsdm.com.cn"
echo "   nslookup www.xsdm.com.cn"
echo ""
echo "6. 重新申请SSL证书："
echo "   sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn"
echo ""
echo "详细故障排查指南："
echo "docs/guides/XSDM_SSL_CERTIFICATE_TROUBLESHOOTING.md"
echo ""