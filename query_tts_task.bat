@echo off
REM MiniMax TTS API 查询任务状态脚本
REM 替换 TASK_ID 为实际的任务ID

set API_KEY=sk-api-aomH3HEEi6b-QcE_ZdQHJJ2gHqKmuoI_0MLPls7bBhKusdA3ief8Zar6x2IHOj7Cjuv7vvGVFnnwYL1czCY7iKOguMt0YAV-2JPoxjPXShcUL8u1zQLa8eo
set GROUP_ID=2017772342268141667

if "%1"=="" (
    echo 用法: query_tts_task.bat ^<task_id^>
    echo 示例: query_tts_task.bat 361945241514069
    pause
    exit /b
)

set TASK_ID=%1

echo.
echo ========================================
echo 查询任务状态: %TASK_ID%
echo ========================================
echo.

curl -X GET "https://api.minimaxi.com/v1/query/t2a_async_query_v2?task_id=%TASK_ID%^&GroupId=%GROUP_ID%" ^
  -H "Authorization: Bearer %API_KEY%" ^
  -H "Content-Type: application/json"

echo.
echo.

pause
