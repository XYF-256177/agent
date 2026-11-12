@echo off
cd /d "%~dp0"
git remote remove origin 2>nul
git remote add origin https://github.com/XYF-256177/agent.git

echo [1/3] Direct force push (no proxy) ...
git config --global http.postBuffer 524288000
git push --force -u origin main
if not errorlevel 1 goto success

echo.
echo [2/3] Via ghproxy.com mirror ...
git remote set-url origin https://ghproxy.com/https://github.com/XYF-256177/agent.git
git push --force -u origin main
if not errorlevel 1 goto success

echo.
echo [3/3] Via ghproxy.net mirror ...
git remote set-url origin https://ghproxy.net/https://github.com/XYF-256177/agent.git
git push --force -u origin main
if not errorlevel 1 goto success

echo.
echo ============================
echo  ALL FAILED.
echo  Try phone hotspot, then re-run.
echo ============================
goto end

:success
echo.
echo ============================
echo  FORCE PUSH SUCCESS! Repo: https://github.com/XYF-256177/agent
echo ============================
:end
pause
