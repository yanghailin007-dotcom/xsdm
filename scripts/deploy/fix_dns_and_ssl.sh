#!/bin/bash
# DNS和SSL证书问题修复脚本
# 使用方法: sudo bash fix_dns_and_ssl.sh

echo "========================================"
echo "  DNS和SSL证书问题修复工具"
echo "========================================"
echo ""

# 步骤1：获取服务器实际IP
echo "🔍 步骤1：确认服务器公网IP"
echo "----------------------------------------"
PUBLIC_IP=$(curl -s ifconfig.me)
echo "服务器公网IP: $PUBLIC_IP"
echo ""

# 步骤2：检查DNS解析
echo "🔍 步骤2：检查DNS解析"
echo "----------------------------------------"
echo "正在检查 xsdm.com.cn 的DNS解析..."
DNS_IP=$(dig +short xsdm.com.cn @8.8.8.8 | head -1)
if [ -n "$DNS_IP" ]; then
    echo "✅ xsdm.com.cn 解析到: $DNS_IP"
    if [ "$DNS_IP" = "$PUBLIC_IP" ]; then
        echo "✅ DNS解析正确，指向服务器IP"
    else
        echo "❌ DNS解析错误！"
        echo "   DNS记录指向: $DNS_IP"
        echo "   服务器实际IP: $PUBLIC_IP"
        echo ""
        echo "⚠️  需要在阿里云DNS控制台修改A记录："
        echo "   登录: https://dns.console.aliyun.com/"
        echo "   将 xsdm.com.cn 的A记录修改为: $PUBLIC_IP"
    fi
else
    echo "❌ DNS解析失败！未找到 xsdm.com.cn 的A记录"
    echo ""
    echo "⚠️  需要在阿里云DNS控制台添加A记录："
    echo "   登录: https://dns.console.aliyun.com/"
    echo "   添加记录:"
    echo "   - 主机记录: @"
    echo "   - 记录类型: A"
    echo "   - 记录值: $PUBLIC_IP"
    echo "   - TTL: 600"
fi
echo ""

echo "正在检查 www.xsdm.com.cn 的DNS解析..."
WWW_DNS_IP=$(dig +short www.xsdm.com.cn @8.8.8.8 | head -1)
if [ -n "$WWW_DNS_IP" ]; then
    echo "✅ www.xsdm.com.cn 解析到: $WWW_DNS_IP"
    if [ "$WWW_DNS_IP" = "$PUBLIC_IP" ]; then
        echo "✅ DNS解析正确，指向服务器IP"
    else
        echo "❌ DNS解析错误！"
        echo "   DNS记录指向: $WWW_DNS_IP"
        echo "   服务器实际IP: $PUBLIC_IP"
        echo ""
        echo "⚠️  需要在阿里云DNS控制台修改A记录："
        echo "   登录: https://dns.console.aliyun.com/"
        echo "   将 www.xsdm.com.cn 的A记录修改为: $PUBLIC_IP"
    fi
else
    echo "❌ DNS解析失败！未找到 www.xsdm.com.cn 的A记录"
    echo ""
    echo "⚠️  需要在阿里云DNS控制台添加A记录："
    echo "   登录: https://dns.console.aliyun.com/"
    echo "   添加记录:"
    echo "   - 主机记录: www"
    echo "   - 记录类型: A"
    echo "   - 记录值: $PUBLIC_IP"
    echo "   - TTL: 600"
fi
echo ""

# 步骤3：检查Nginx配置
echo "🔍 步骤3：检查Nginx配置"
echo "----------------------------------------"
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx正在运行"
else
    echo "❌ Nginx未运行，正在启动..."
    systemctl start nginx
fi

if nginx -t 2>&1 | grep -q "successful"; then
    echo "✅ Nginx配置正确"
else
    echo "❌ Nginx配置有错误"
    nginx -t
fi

# 检查80端口
if netstat -tlnp | grep -q ":80 "; then
    echo "✅ 80端口正在监听"
else
    echo "❌ 80端口未监听"
fi
echo ""

# 步骤4：检查防火墙
echo "🔍 步骤4：检查防火墙配置"
echo "----------------------------------------"
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "80.*ALLOW"; then
        echo "✅ 防火墙已开放80端口"
    else
        echo "⚠️  防火墙未开放80端口，正在添加..."
        ufw allow 80/tcp
        ufw allow 443/tcp
        echo "✅ 防火墙规则已添加"
    fi
else
    echo "⚠️  未检测到UFW防火墙"
fi
echo ""

# 步骤5：测试本地访问
echo "🔍 步骤5：测试本地HTTP访问"
echo "----------------------------------------"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "✅ 本地HTTP访问正常 (HTTP $HTTP_CODE)"
else
    echo "⚠️  本地HTTP访问异常 (HTTP $HTTP_CODE)"
fi
echo ""

# 步骤6：总结和建议
echo "========================================"
echo "  诊断总结和建议"
echo "========================================"
echo ""
echo "服务器公网IP: $PUBLIC_IP"
echo ""

# 检查DNS是否需要修复
if [ "$DNS_IP" != "$PUBLIC_IP" ] || [ -z "$DNS_IP" ]; then
    echo "🔧 需要修复的配置："
    echo ""
    echo "1. 登录阿里云DNS控制台: https://dns.console.aliyun.com/"
    echo ""
    echo "2. 修改/添加以下A记录："
    echo ""
    echo "   记录1："
    echo "   - 主机记录: @"
    echo "   - 记录类型: A"
    echo "   - 记录值: $PUBLIC_IP"
    echo "   - TTL: 600"
    echo ""
    echo "   记录2："
    echo "   - 主机记录: www"
    echo "   - 记录类型: A"
    echo "   - 记录值: $PUBLIC_IP"
    echo "   - TTL: 600"
    echo ""
    echo "3. 保存后等待DNS生效（10-30分钟）"
    echo ""
    echo "4. 验证DNS解析（在本地电脑执行）："
    echo "   nslookup xsdm.com.cn"
    echo "   nslookup www.xsdm.com.cn"
    echo ""
    echo "5. DNS生效后，重新申请SSL证书："
    echo "   sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn"
    echo ""
else
    echo "✅ DNS配置正确！"
    echo ""
    echo "如果SSL证书申请仍然失败，可能是因为："
    echo "1. DNS还未完全生效（全球传播需要时间）"
    echo "2. Let's Encrypt的验证服务器缓存未更新"
    echo ""
    echo "建议："
    echo "1. 等待10-30分钟后重试"
    echo "2. 使用 --force-renewal 强制续期："
    echo "   sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn --force-renewal"
    echo ""
fi

echo "📖 详细故障排查指南："
echo "docs/guides/XSDM_SSL_CERTIFICATE_TROUBLESHOOTING.md"
echo ""