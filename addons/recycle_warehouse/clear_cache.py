#!/usr/bin/env python3
"""
Run this script to clear Odoo asset cache and force rebuild.
Usage: docker exec odoo19 python3 /mnt/extra-addons/recycle_warehouse/clear_cache.py
"""
import subprocess, sys

SQL = """
DELETE FROM ir_attachment 
WHERE url LIKE '/web/content/%' 
  AND (name LIKE '%assets%' OR name LIKE '%.min.js' OR name LIKE '%.min.css' OR name LIKE '%bundle%');
"""
print("This file is just a reference - use FULL_RESET.bat instead")
