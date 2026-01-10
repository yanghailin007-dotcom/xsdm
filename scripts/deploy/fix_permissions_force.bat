@echo off
chcp 65001 >nul
echo ========================================
echo    强制修复私钥文件权限
echo ========================================
echo.

set KEY_PATH=d:\work6.05\xsdm.pem

echo 当前进度:
echo.
echo 步骤 1/4: 查看当前权限...
echo ----------------------------------------
icacls "%KEY_PATH%"
echo.

echo 步骤 2/4: 移除所有继承权限...
echo ----------------------------------------
icacls "%KEY_PATH%" /inheritance:d
echo.
echo ✓ 完成
echo.

echo 步骤 3/4: 移除所有用户权限...
echo ----------------------------------------
icacls "%KEY_PATH%" /remove "*S-1-5-11"
icacls "%KEY_PATH%" /remove "NT AUTHORITY\Authenticated Users"
icacls "%KEY_PATH%" /remove "NT AUTHORITY\SYSTEM"
echo.
echo ✓ 完成
echo.

echo 步骤 4/4: 只授予当前用户完全控制权限...
echo ----------------------------------------
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F"
echo.
echo ✓ 完成
echo.

echo ========================================
echo 验证修复结果
echo ========================================
echo.
icacls "%KEY_PATH%"
echo.

echo ========================================
echo 权限修复完成！
echo ========================================
echo.
echo 现在请测试SSH连接:
echo.
echo ssh -i "%KEY_PATH%" admin@8.163.37.124 "echo '连接成功！'"
echo.

pause