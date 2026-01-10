@echo off
chcp 65001 >nul
echo ========================================
echo    测试SSH连接（简化版）
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set KEY_PATH=d:\work6.05\xsdm.pem

echo 测试1: 使用admin用户
echo ---------------------------------------
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes admin@%SERVER_IP% "echo '连接成功！'" 2>&1
echo.

echo 测试2: 使用root用户（轻量应用服务器默认）
echo ---------------------------------------
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes root@%SERVER_IP% "echo '连接成功！'" 2>&1
echo.

echo ========================================
echo 诊断结果
echo ========================================
echo.
echo 如果上面任何一个测试显示"连接成功！"，说明SSH可以工作
echo 如果都失败了，可能需要:
echo.
echo 1. 在阿里云控制台使用Workbench连接
echo 2. 检查密钥对是否已绑定到实例
echo 3. 确认服务器操作系统类型和默认用户名
echo.
pause