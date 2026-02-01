@echo off
REM MiniMax TTS API 测试脚本
REM 请先替换 YOUR_API_KEY 为你的实际API密钥

set API_KEY=sk-api-aomH3HEEi6b-QcE_ZdQHJJ2gHqKmuoI_0MLPls7bBhKusdA3ief8Zar6x2IHOj7Cjuv7vvGVFnnwYL1czCY7iKOguMt0YAV-2JPoxjPXShcUL8u1zQLa8eo
set GROUP_ID=2017772342268141667

echo.
echo ========================================
echo MiniMax TTS API 测试
echo ========================================
echo.

echo 1. 提交异步TTS任务...
curl -X POST "https://api.minimaxi.com/v1/t2a_async_v2?GroupId=%GROUP_ID%" ^
  -H "Authorization: Bearer %API_KEY%" ^
  -H "Content-Type: application/json" ^
  -d "^{
    \"model\": \"speech-2.8-turbo\",
    \"text\": \"你好，这是一个测试语音合成。\",
    \"voice_setting\": {
      \"voice_id\": \"audiobook_male_1\",
      \"speed\": 1.0,
      \"vol\": 1.0,
      \"pitch\": 0
    },
    \"audio_setting\": {
      \"audio_sample_rate\": 32000,
      \"bitrate\": 128000,
      \"format\": \"mp3\",
      \"channel\": 1
    },
    \"language_boost\": \"Chinese\"
  }^"

echo.
echo.
echo ========================================
echo 注意：请复制上面返回的 task_id，然后运行查询脚本
echo ========================================
echo.

pause
