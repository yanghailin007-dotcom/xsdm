@echo off
chcp 65001 >nul
echo ========================================
echo    强制更新前端文件
echo ========================================
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo 步骤 1/3: 上传前端静态文件...
echo.

REM 上传所有CSS文件
echo 上传CSS文件...
scp -i "%KEY_PATH%" -r -o StrictHostKeyCheckingno web/static/css %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/static/

REM 上传所有JS文件
echo 上传JS文件...
scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no web/static/js %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/static/

REM 上传所有HTML模板
echo 上传HTML模板...
scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no web/templates %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/

REM 上传路由和API文件
echo 上传路由和API文件...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no web/routes/*.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/routes/
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no web/api/*.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/api/

echo ✓ 前端文件上传完成
echo.

echo 步骤 2/3: 清理服务器缓存...
echo.
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && find web/static -name '*.pyc' -delete && find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo '✓ 缓存清理完成'"

echo.
echo 步骤 3/3: 重启服务...
echo.
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && source venv/bin/activate && lsof -ti:5000 | xargs kill -9 2>/dev/null && sleep 2 && nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 & sleep 3 && if lsof -ti:5000 >/dev/null 2>&1; then echo '✓ 服务重启成功'; else echo '❌ 服务重启失败'; fi"

echo.
echo ========================================
echo    ✓ 前端更新完成！
echo ========================================
echo.
echo 重要提示：
echo 1. 请强制刷新浏览器（Ctrl+F5 或 Ctrl+Shift+R）
echo 2. 清除浏览器缓存：
echo    - Chrome: F12 → Network → Disable cache → 刷新
echo    - 或使用无痕模式访问
echo.
echo 访问地址: http://%SERVER_IP%:5000
echo.

pause