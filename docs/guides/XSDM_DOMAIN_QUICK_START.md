# xsdm.com.cn 域名配置快速参考

## 快速配置步骤（5步完成）

### 步骤1：配置DNS解析（阿里云控制台）

访问：https://dns.console.aliyun.com/

添加两条A记录：

| 主机记录 | 记录类型 | 记录值 | TTL |
|---------|---------|--------|-----|
| @ | A | 8.163.37.124 | 600 |
| www | A | 8.163.37.124 | 600 |

**验证DNS生效**：
```cmd
nslookup xsdm.com.cn
```

---

### 步骤2：上传并执行配置脚本（服务器端）

**在本地Windows电脑执行**：
```cmd
scp -i "d:\work6.05\xsdm.pem" scripts\deploy\setup_xsdm_domain.sh root@8.163.37.124:/root/
```

**连接服务器**：
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
```

**执行配置脚本**：
```bash
chmod +x /root/setup_xsdm_domain.sh
sudo bash /root/setup_xsdm_domain.sh
```

---

### 步骤3：配置阿里云安全组

在阿里云ECS控制台添加安全组规则：

| 端口 | 协议 | 授权对象 | 描述 |
|-----|------|---------|------|
| 80 | TCP | 0.0.0.0/0 | HTTP |
| 443 | TCP | 0.0.0.0/0 | HTTPS |

---

### 步骤4：等待DNS生效并验证

**等待10-30分钟**，然后测试访问：
- http://xsdm.com.cn
- http://www.xsdm.com.cn

---

### 步骤5：申请SSL证书（HTTPS）

**DNS生效后，在服务器执行**：
```bash
sudo certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn
```

按提示操作：
1. 输入邮箱地址
2. 输入 `A` 同意服务条款
3. 输入 `N` 不共享邮箱
4. 选择 `2: Redirect` 重定向HTTP到HTTPS

**验证HTTPS访问**：
- https://xsdm.com.cn
- https://www.xsdm.com.cn

---

## 常用命令

### 检查Nginx状态
```bash
systemctl status nginx
```

### 查看Nginx日志
```bash
tail -f /var/log/nginx/xsdm-error.log
```

### 重启Nginx
```bash
systemctl restart nginx
```

### 检查SSL证书
```bash
certbot certificates
```

### 测试Nginx配置
```bash
nginx -t
```

---

## 故障排查

### 问题1：无法访问域名

**检查**：
```bash
# 1. DNS是否生效
nslookup xsdm.com.cn

# 2. Nginx是否运行
systemctl status nginx

# 3. 端口是否开放
netstat -tlnp | grep :80
```

### 问题2：502 Bad Gateway

**检查**：
```bash
# 检查后端应用
supervisorctl status novel-system

# 检查8080端口
netstat -tlnp | grep 8080
```

### 问题3：SSL证书申请失败

**检查**：
```bash
# 确认80端口开放
netstat -tlnp | grep :80

# 确认DNS已生效
dig xsdm.com.cn +short
```

---

## 配置完成验证清单

- [ ] DNS解析已配置（@ 和 www 都指向 8.163.37.124）
- [ ] DNS解析已生效（nslookup验证）
- [ ] Nginx已安装并运行
- [ ] 防火墙已开放80和443端口
- [ ] 阿里云安全组已开放80和443端口
- [ ] HTTP访问正常（http://xsdm.com.cn）
- [ ] SSL证书已申请成功
- [ ] HTTPS访问正常（https://xsdm.com.cn）
- [ ] HTTP自动重定向到HTTPS

---

## 完整文档

详细配置说明请参考：[docs/guides/XSDM_DOMAIN_SETUP_GUIDE.md](XSDM_DOMAIN_SETUP_GUIDE.md)