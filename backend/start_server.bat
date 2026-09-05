@echo off
setlocal
if "%KOSMIK_ADMIN_PASSWORD%"=="" (
  echo Set KOSMIK_ADMIN_PASSWORD before starting the server.
  echo Example: set KOSMIK_ADMIN_PASSWORD=use-a-long-random-password
  exit /b 1
)
python backend\server.py
