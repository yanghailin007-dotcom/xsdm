#!/bin/bash
# SSL证书申请脚本 - 针对已配置DNS的情况
# 使用方法: sudo bash apply_ssl_certificate.sh

echo "========================================"
echo "  SSL证书申请工具"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 步骤1：验证DNS解析
echo "🔍 步骤1：验证DNS解析"
echo "----------------------------------------"

# 从多个DNS服务器查询验证
echo "从多个DNS服务器验证 xsdm.com.cn 的解析..."

GOOGLE_DNS=$(dig +short xsdm.com.cn @8.8.8.8 | head -1)
CLOUDFLARE_DNS=$(dig +short xsdm.com.cn @1.1.1.1 | head -1)
ALIDNS_DNS=$(dig +short xsdm.com.cn @223.5.5.5 | head -1)

echo "Google DNS (8.8.8.8): $GOOGLE_DNS"
echo "Cloudflare DNS (1.1.1.1): $CLOUDFLARE_DNS"
echo "阿里DNS (223.5.5.5): $ALIDNS_DNS"

if [ -n "$GOOGLE_DNS" ] && [ "$GOOGLE_DNS" != "" ]; then
    echo -e "${GREEN}✅ DNS解析正常${NC}"
else
    echo -e "${YELLOW}⚠️  DNS解析可能还未完全传播${NC}"
fi
echo ""

# 步骤2：测试HTTP访问
echo "🔍 步骤2：测试HTTP访问"
echo "----------------------------------------"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "${GREEN}✅ 本地HTTP访问正常 (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️  本地HTTP访问异常 (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# 步骤3：检查Nginx配置
echo "🔍 步骤3：检查Nginx配置"
echo "----------------------------------------"
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx正在运行${NC}"
else
    echo "❌ Nginx未运行，正在启动..."
    systemctl start nginx
fi

if netstat -tlnp | grep -q ":80 "; then
    echo -e "${GREEN}✅ 80端口正在监听${NC}"
else
    echo "❌ 80端口未监听"
fi
echo ""

# 步骤4：申请SSL证书
echo "========================================"
echo "  申请SSL证书"
echo "========================================"
echo ""
echo "准备申请SSL证书..."
echo "域名: xsdm.com.cn, www.xsdm.com.cn"
echo ""
echo "如果申请失败，可能原因："
echo "1. DNS全球传播还未完成（需要等待）"
echo "2. Let's Encrypt验证服务器缓存未更新"
echo "3. 临时网络问题"
echo ""

# 方法1：标准申请
echo "方法1：标准申请（推荐）"
echo "命令：sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn"
echo ""
read -p "是否继续？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SSL证书申请成功！${NC}"
        exit 0
    fi
fi

echo ""

# 方法2：强制续期
echo "方法2：强制续期（如果标准方法失败）"
echo "命令：sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn --force-renewal"
echo ""
read -p "是否尝试强制续期？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn --force-renewal
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SSL证书申请成功！${NC}"
        exit 0
    fi
fi

echo ""

# 方法3：只申请主域名
echo "方法3：只申请主域名 xsdm.com.cn（不包含www）"
echo "命令：sudo certbot --nginx -d xsdm.com.cn"
echo ""
read -p "是否尝试只申请主域名？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    certbot --nginx -d xsdm.com.cn
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SSL证书申请成功！${NC}"
        echo "注意：www.xsdm.com.cn 将不包含在证书中"
        exit 0
    fi
fi

echo ""
echo "========================================"
echo "  所有方法都失败了"
echo "========================================"
echo ""
echo "可能的原因和解决方案："
echo ""
echo "1. DNS传播延迟："
echo "   - 全球DNS传播可能需要24-48小时"
echo "   - 虽然本地DNS已更新，但Let's Encrypt的验证服务器可能还在使用旧数据"
echo "   - 建议：等待1-2小时后重试"
echo ""
echo "2. 验证服务器缓存："
echo "   - Let's Encrypt的DNS缓存可能还未更新"
echo "   - 建议：等待30分钟后重试"
echo ""
echo "3. 临时解决方案："
echo "   - 暂时使用HTTP访问（已配置好）"
echo "   - 稍后再申请SSL证书"
echo ""
echo "4. 手动验证DNS："
echo "   在本地电脑执行："
echo "   nslookup xsdm.com.cn"
echo "   nslookup www.xsdm.com.cn"
echo ""
echo "5. 查看详细日志："
echo "   sudo tail -100 /var/log/letsencrypt/letsencrypt.log"
echo ""
echo "建议操作："
echo "1. 等待30分钟到2小时"
echo "2. 重新运行此脚本"
echo "3. 或者使用只申请主域名的方法"
echo ""