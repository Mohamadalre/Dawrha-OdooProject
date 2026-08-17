@echo off
REM ============================================================
REM  Recycle WMS - DIAGNOSTICS  (read-only, safe)
REM  Shows containers, databases, PDF engine, and recent logs.
REM ============================================================
cd /d "%~dp0"
echo ============================================================
echo   RECYCLE WMS - DIAGNOSTICS
echo ============================================================
echo.
echo [1] Container status
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
echo [2] Databases
docker exec odoo19-db psql -U odoo -d postgres -c "\l"
echo.
echo [3] PDF engine (wkhtmltopdf)
docker exec odoo19 wkhtmltopdf --version
echo.
echo [4] Last 80 Odoo log lines
docker logs odoo19 --tail=80
echo.
echo ============================================================
echo  Done. App: http://localhost:8069/odoo
echo ============================================================
pause
