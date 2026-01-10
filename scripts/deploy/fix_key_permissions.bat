@echo off
chcp 65001 >nul
echo ========================================
echo    修复私钥文件权限
echo ========================================
echo.

set KEY_PATH=d:\work6.05\xsdm.pem

echo 正在修复私钥文件权限...
echo 文件: %KEY_PATH%
echo.

REM 移除继承的权限
echo 步骤 1/3: 移除继承的权限...
icacls "%KEY_PATH%" /inheritance:r
if %ERRORLEVEL% neq 0 (
    echo ❌ 移除继承权限失败
    pause
    exit /b 1
)
echo ✓ 完成
echo.

REM 授予当前用户完全控制权限
echo 步骤 2/3: 授予当前用户完全控制权限...
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F"
if %ERRORLEVEL% neq 0 (
    echo ❌ 授予权限失败
    pause
    exit /b 1
)
echo ✓ 完成
echo.

REM 验证权限
echo 步骤 3/3: 验证权限...
icacls "%KEY_PATH%"
echo.

echo ========================================
echo ✓ 权限修复完成！
echo ========================================
echo.

echo 现在可以测试SSH连接:
echo.
echo ssh -i "%KEY_PATH%" admin@8.163.37.124 "echo '连接成功！'"
echo.

echo 或运行部署工具:
echo.
echo cd d:\work6.05
echo scripts\deploy\quick_start.bat
echo.

pause