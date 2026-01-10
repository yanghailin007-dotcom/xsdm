# 快速部署指南 - 解决2.9GB代码同步慢的问题

## 问题分析

你的项目总大小约 **2.9GB**，但实际上服务器只需要：

| 目录 | 大小 | 需要部署 | 说明 |
|------|------|----------|------|
| Chrome/ | 1.6GB | ❌ | 浏览器自动化，服务器不需要 |
| .git/ | 605MB | ❌ | Git历史，不需要部署 |
| generated_images/ | 39MB | ❌ | 生成的图片，不应同步 |
| .venv/ | 15MB | ❌ | 虚拟环境，服务器重新创建 |
| src/ | 5MB | ✅ | 核心代码 |
| web/ | 9MB | ✅ | Web界面 |
| config/ | 0.05MB | ✅ | 配置文件 |
| scripts/ | 0.3MB | ✅ | 脚本工具 |
| requirements.txt | <1MB | ✅ | 依赖列表 |

**实际需要同步：约 30MB**（只需几秒钟！）

---

## 解决方案

### 方案1：使用智能部署脚本（推荐）⭐

**优势：**
- ✅ 只同步必要的代码（~30MB）
- ✅ 支持增量更新（只传输变化的文件）
- ✅ 自动排除无用文件
- ✅ 显示同步进度

#### Windows使用方法：

```batch
# 1. 安装 rsync（如果还没有）
choco install rsync

# 2. 运行智能部署脚本
cd d:\work6.05
scripts\deploy\smart_deploy.bat
```

#### Linux/Mac使用方法：

```bash
# 运行智能部署脚本
cd d:\work6.05
bash scripts/deploy/smart_deploy.sh
```

**同步时间：首次约30秒，后续更新只需几秒钟！**

---

### 方案2：使用Git部署（最专业）⭐⭐⭐

**优势：**
- ✅ 只传输Git跟踪的代码（更小）
- ✅ 版本控制，可以回滚
- ✅ 支持分支管理
- ✅ 适合团队协作

#### 步骤1：确保.gitignore正确配置

```bash
# 检查.gitignore已排除大文件
cat .gitignore
```

确认排除：
- `Chrome/`
- `.venv/`
- `generated_images/`
- `logs/`
- `小说项目/`
- `*.db`
- `*.log`

#### 步骤2：提交代码到Git

```bash
cd d:\work6.05
git add .
git commit -m "准备部署到服务器"
git push origin main
```

#### 步骤3：在服务器上克隆

```bash
# SSH连接服务器
ssh -i d:/work6.05/xsdm.pem root@8.163.37.124

# 克隆代码
cd /home/novelapp
git clone https://github.com/你的用户名/你的仓库.git novel-system

# 或使用SSH密钥（推荐）
git clone git@github.com:你的用户名/你的仓库.git novel-system
```

#### 步骤4：更新部署（超级快！）

```bash
# 在服务器上
cd /home/novelapp/novel-system
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart novel-system
```

**更新时间：只需几秒钟！**

---

### 方案3：使用rsync直接同步（快速）

**优势：**
- ✅ 快速同步
- ✅ 增量传输
- ✅ 可以手动控制排除规则

#### Windows命令：

```batch
rsync -avz --progress ^
  --exclude="Chrome/" ^
  --exclude=".git/" ^
  --exclude=".venv/" ^
  --exclude="generated_images/" ^
  --exclude="logs/" ^
  --exclude="小说项目/" ^
  --exclude="__pycache__/" ^
  --exclude="*.pyc" ^
  -e "ssh -i d:/work6.05/xsdm.pem" ^
  d:/work6.05/ ^
  novelapp@8.163.37.124:/home/novelapp/novel-system/
```

#### Linux/Mac命令：

```bash
rsync -avz --progress \
  --exclude='Chrome/' \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='generated_images/' \
  --exclude='logs/' \
  --exclude='小说项目/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  -e "ssh -i d:/work6.05/xsdm.pem" \
  d:/work6.05/ \
  novelapp@8.163.37.124:/home/novelapp/novel-system/
```

---

### 方案4：首次使用tar打包+rsync（最快首次部署）

**优势：**
- ✅ 首次部署更快
- ✅ 减少小文件传输开销
- ✅ 适合首次部署

#### Windows命令：

```batch
# 1. 创建部署包（只包含必要文件）
tar -czf deploy_package.tar.gz ^
  --exclude="Chrome" ^
  --exclude=".git" ^
  --exclude=".venv" ^
  --exclude="generated_images" ^
  --exclude="logs" ^
  --exclude="小说项目" ^
  --exclude="__pycache__" ^
  --exclude="*.pyc" ^
  --exclude="test_*.py" ^
  --exclude="*.db" ^
  --exclude="*.log" ^
  -C d:/work6.05 .

# 2. 上传到服务器
scp -i d:/work6.05/xsdm.pem deploy_package.tar.gz novelapp@8.163.37.124:/tmp/

# 3. 在服务器上解压
ssh -i d:/work6.05/xsdm.pem novelapp@8.163.37.124 "cd /home/novelapp && tar -xzf /tmp/deploy_package.tar.gz -C novel-system"

# 4. 清理
del deploy_package.tar.gz
ssh -i d:/work6.05/xsdm.pem novelapp@8.163.37.124 "rm /tmp/deploy_package.tar.gz"
```

---

## 推荐工作流

### 开发环境（本地Windows）

```batch
# 1. 正常开发
python scripts/start_server.py

# 2. 提交代码
git add .
git commit -m "描述你的更改"
git push
```

### 生产环境（服务器）

```bash
# 1. 更新代码（只需几秒）
cd /home/novelapp/novel-system
git pull origin main

# 2. 如果有新依赖
source venv/bin/activate
pip install -r requirements.txt

# 3. 重启服务
sudo supervisorctl restart novel-system
```

---

## 性能对比

| 方案 | 首次同步 | 后续更新 | 难度 | 推荐度 |
|------|----------|----------|------|--------|
| 全量复制 | 2.9GB/10分钟 | 2.9GB/10分钟 | ⭐ | ❌ |
| 智能rsync | 30MB/30秒 | <1MB/几秒 | ⭐⭐ | ✅ |
| Git部署 | 30MB/1分钟 | <1KB/1秒 | ⭐⭐⭐ | ⭐⭐⭐ |
| tar+rsync | 30MB/20秒 | 30MB/20秒 | ⭐⭐ | ⭐⭐ |

---

## 常见问题

### Q1: 如何排除特定文件？

**A:** 在 `.gitignore` 中添加：

```gitignore
# 数据文件
*.db
*.sqlite

# 日志文件
*.log
logs/

# 生成的文件
generated_images/
temp_fanqie_upload/

# 测试文件
test_*.py
check_*.py
```

### Q2: 如何快速查看会同步哪些文件？

**A:** 使用 `--dry-run` 参数：

```bash
rsync -avz --dry-run \
  --exclude='Chrome/' \
  --exclude='.git/' \
  d:/work6.05/ \
  novelapp@8.163.37.124:/tmp/test/
```

### Q3: 如何检查大文件？

**A:** 在项目根目录运行：

```bash
# 查找大于10MB的文件
powershell -Command "Get-ChildItem -Recurse | Where-Object {$_.Length -gt 10MB} | Sort-Object Length -Descending | Select-Object Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}} | Format-Table -AutoSize"
```

### Q4: 如何清理.git历史减少大小？

**A:** 如果Git历史太大（你的有605MB），可以考虑：

```bash
# 1. 备份当前仓库
cp -r .git .git.backup

# 2. 清理历史（谨慎使用）
git gc --aggressive --prune=now

# 3. 或者创建一个干净的仓库
cd ..
git clone --depth 1 old-repo new-repo
```

---

## 立即开始

### 最快方式（3分钟完成）：

1. **安装rsync**（如果没有）
   ```batch
   choco install rsync
   ```

2. **运行智能部署**
   ```batch
   cd d:\work6.05
   scripts\deploy\smart_deploy.bat
   ```

3. **等待30秒同步完成** ✅

4. **在服务器上完成配置**
   ```bash
   ssh -i d:/work6.05/xsdm.pem novelapp@8.163.37.124
   cd /home/novelapp/novel-system
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   vim .env
   sudo supervisorctl restart novel-system
   ```

---

## 总结

**最佳实践：**
1. ✅ 使用Git管理代码（版本控制+快速部署）
2. ✅ 配置好.gitignore（排除大文件）
3. ✅ 使用智能部署脚本（首次部署）
4. ✅ 后续使用git pull（秒级更新）

**性能提升：**
- 首次部署：从10分钟 → 30秒（**20倍提升**）
- 后续更新：从10分钟 → 1秒（**600倍提升**）

从此告别漫长的部署等待！🚀