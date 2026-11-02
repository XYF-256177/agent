@echo off
cd /d "%~dp0"
echo ============================================
echo   Push WITHOUT Clash - try multiple methods
echo ============================================

git remote remove origin 2>nul
git remote add origin https://github.com/XYF-256177/agent.git

echo [1/4] Direct push (no proxy) ...
git config --global http.postBuffer 524288000
git push -u origin main
if not errorlevel 1 goto success

echo.
echo [2/4] Via ghproxy.com mirror ...
git remote set-url origin https://ghproxy.com/https://github.com/XYF-256177/agent.git
git push -u origin main
if not errorlevel 1 goto success

echo.
echo [3/4] Via ghproxy.net mirror ...
git remote set-url origin https://ghproxy.net/https://github.com/XYF-256177/agent.git
git push -u origin main
if not errorlevel 1 goto success

echo.
echo [4/4] Via SSH (need SSH key added to GitHub) ...
git remote set-url origin git@github.com:XYF-256177/agent.git
git push -u origin main
if not errorlevel 1 goto success

echo.
echo ============================================
echo  ALL FAILED.
echo  Try: (a) phone hotspot, (b) Gitee repo instead.
echo ============================================
goto end

:success
echo.
echo ============================================
echo  PUSH SUCCESS! Repo: https://github.com/XYF-256177/agent
echo  Send this URL to the reviewer.
echo ============================================
:end
pause
