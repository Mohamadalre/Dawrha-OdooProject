@echo off
REM ============================================================
REM  Recycle WMS - UPGRADE  (apply Python / XML / JS changes)
REM  Clears compiled assets, upgrades the module, restarts.
REM  Safe: does NOT delete any database data.
REM ============================================================
cd /d "%~dp0"
echo [1/3] Clearing compiled asset cache...
docker exec odoo19-db psql -U odoo -d odoo19 -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%%';"
echo [2/3] Upgrading module recycle_warehouse...
docker compose run --rm odoo odoo -d odoo19 -u recycle_warehouse --stop-after-init
echo [3/3] Starting Odoo...
docker compose up -d
echo.
echo ============================================================
echo  Done. Open http://localhost:8069/odoo
echo  Then press Ctrl+Shift+R in the browser to hard refresh.
echo ============================================================
pause
