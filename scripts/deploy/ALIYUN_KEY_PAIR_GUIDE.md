# 阿里云ECS密钥对创建和使用指南

## 🔑 什么是密钥对？

密钥对（Key Pair）用于SSH免密登录服务器，包含：
- **公钥**：保存在服务器上
- **私钥**：保存在本地，用于连接服务器

## 📋 方法1：在阿里云控制台创建密钥对（推荐）

### 步骤1：登录阿里云控制台

访问：https://ecs.console.aliyun.com/

### 步骤2：进入密钥对管理

1. 在左侧菜单找到 **"网络和安全"**
2. 点击 **"密钥对"**

### 步骤3：创建新的密钥对

1. 点击 **"创建密钥对"** 按钮
2. 填写信息：
   - **密钥对名称**：例如 `my-server-key` 或 `novel-app-key`
   - **类型**：选择 **"SSH密钥对"**
3. 点击 **"确定"** 创建

### 步骤4：下载私钥文件

⚠️ **重要**：私钥文件**只能下载一次**，请妥善保管！

1. 创建后会自动下载 `.pem` 格式的私钥文件
2. 文件名通常是：`密钥对名称.pem`
3. 将文件保存到安全的位置，例如：
   - Windows: `C:\Users\您的用户名\.ssh\aliyun-key.pem`
   - 或其他安全目录

### 步骤5：绑定密钥对到ECS实例

1. 在密钥对列表中，找到刚创建的密钥对
2. 点击 **"绑定密钥对"**
3. 选择您的ECS实例（IP为 172.18.60.76 的实例）
4. 点击 **"确定"** 绑定

### 步骤6：重置实例（如果需要）

如果服务器已经在运行，可能需要重启实例才能使用新的密钥对：
1. 在ECS实例列表中
2. 选择您的实例
3. 点击 **"更多"** → **"实例状态"** → **"重启"**

## 📋 方法2：使用现有密钥对

### 查找已创建的密钥对

1. 登录阿里云ECS控制台
2. 进入 **"网络和安全"** → **"密钥对"**
3. 查看已有的密钥对列表

### 重新下载私钥（如果丢失）

⚠️ **注意**：如果私钥文件丢失且没有备份，**无法重新下载**！

**解决方案**：
1. 创建新的密钥对
2. 绑定到服务器
3. 删除旧的密钥对绑定

## 🔐 私钥文件安全设置

### Windows权限设置

在本地Windows上，私钥文件需要设置正确的权限：

1. **右键点击**私钥文件（例如 `aliyun-key.pem`）
2. 选择 **"属性"**
3. 点击 **"安全"** 选项卡
4. 点击 **"高级"**
5. 点击 **"禁用继承"**
6. 选择 **"将已继承的权限转换为此对象的显式权限"**
7. 删除所有用户，只保留您的用户账户
8. 独占访问权限：**完全控制**

### 或使用PowerShell设置权限

```powershell
# 设置私钥文件权限（仅当前用户可读）
icacls "C:\path\to\aliyun-key.pem" /inheritance:r
icacls "C:\path\to\aliyun-key.pem" /grant:r "$env:USERNAME:F"
```

## 🔑 使用密钥对连接服务器

### 方法1：使用SSH命令

```powershell
# PowerShell或CMD
ssh -i "C:\path\to\aliyun-key.pem" admin@您的公网IP

# 第一次连接会提示确认主机指纹，输入 yes
```

### 方法2：使用批处理工具

```cmd
cd d:\work6.05
scripts\deploy\connect_and_deploy.bat

# 输入私钥文件路径时，填写您的.pem文件完整路径
```

### 方法3：使用PuTTY

需要先转换密钥格式：

1. **打开PuTTYgen**
   - 下载：https://www.putty.org/

2. **加载.pem文件**
   - 点击 **"Load"**
   - 选择您的 `.pem` 文件
   - 点击 **"Save private key"**
   - 保存为 `.ppk` 格式

3. **使用PuTTY连接**
   - **Host Name**: 您的公网IP
   - **Port**: 22
   - **Connection** → **SSH** → **Auth** → **Credentials**
   - **Private key file**: 选择 `.ppk` 文件
   - 点击 **"Open"** 连接

## 🔍 验证密钥对是否生效

### 测试连接

```powershell
# 测试SSH连接
ssh -i "C:\path\to\aliyun-key.pem" -o ConnectTimeout=10 admin@您的公网IP "echo '连接成功！'"

# 如果显示"连接成功！"，说明密钥配置正确
```

### 在服务器上查看

```bash
# SSH登录后，查看授权的密钥
cat ~/.ssh/authorized_keys

# 查看私钥权限（在本地Windows）
icacls "C:\path\to\aliyun-key.pem"
```

## 🆨 常见问题

### 问题1：无法使用密钥登录

**可能原因**：
1. 密钥对未绑定到服务器
2. 服务器使用的是密码认证而不是密钥认证
3. 私钥文件权限不正确

**解决方案**：
```bash
# 在服务器上检查SSH配置
sudo vim /etc/ssh/sshd_config

# 确保以下配置：
PubkeyAuthentication yes
PasswordAuthentication no  # 可选：禁用密码登录

# 重启SSH服务
sudo systemctl restart sshd
```

### 问题2：私钥文件权限错误

**Windows错误提示**：
```
Permissions 0644 for 'aliyun-key.pem' are too open.
```

**解决方案**：
```powershell
# 使用PowerShell设置权限
icacls "C:\path\to\aliyun-key.pem" /inheritance:r
icacls "C:\path\to\aliyun-key.pem" /grant:r "$env:USERNAME:F"
```

### 问题3：找不到密钥对

**检查步骤**：
1. 确认在阿里云控制台的 **"密钥对"** 页面
2. 确认选择的区域是否正确（与ECS实例在同一区域）
3. 确认密钥对是否已绑定到实例

### 问题4：私钥文件丢失

**解决方案**：
1. 创建新的密钥对
2. 绑定到服务器
3. 删除旧密钥对的绑定

## 📋 快速检查清单

部署前请确认：

- [ ] 已在阿里云控制台创建密钥对
- [ ] 已下载并保存私钥文件（.pem格式）
- [ ] 密钥对已绑定到ECS实例
- [ ] 私钥文件保存在安全位置
- [ ] 私钥文件权限设置正确
- [ ] 可以使用私钥成功连接服务器
- [ ] 已获取服务器公网IP
- [ ] 已配置安全组规则（开放22端口）

## 🎯 完整流程示例

```powershell
# 1. 在阿里云控制台创建密钥对（上面已说明）
# 2. 下载私钥到本地：C:\Users\您的用户名\.ssh\aliyun-key.pem

# 3. 设置私钥权限
icacls "C:\Users\您的用户名\.ssh\aliyun-key.pem" /inheritance:r
icacls "C:\Users\您的用户名\.ssh\aliyun-key.pem" /grant:r "$env:USERNAME:F"

# 4. 测试连接
ssh -i "C:\Users\您的用户名\.ssh\aliyun-key.pem" admin@您的公网IP

# 5. 使用部署工具
cd d:\work6.05
scripts\deploy\connect_and_deploy.bat
```

## 📞 获取帮助

- **阿里云文档**：https://help.aliyun.com/document_detail/51793.html
- **密钥对管理**：https://ecs.console.aliyun.com/#/keyPair/region/cn-hangzhou
- **详细部署指南**：`scripts/deploy/LOCAL_TO_ALIYUN_DEPLOYMENT_GUIDE.md`

## ⚠️ 安全建议

1. **不要泄露私钥**：私钥文件等同于您的服务器密码
2. **定期更换密钥**：建议每3-6个月更换一次
3. **使用强密码**：即使使用密钥，也要设置强密码作为备份
4. **备份私钥**：在多个安全位置备份私钥文件
5. **禁用密码登录**：配置密钥后，建议禁用密码登录

---

现在您知道如何创建和使用阿里云密钥对了！按照上面的步骤操作，您就可以安全地连接到您的服务器。