# ── Dawrha — Odoo 19 image with the recycle_warehouse addon baked in ──────────
#
# Built on the official Odoo image (which already ships PostgreSQL client libs,
# wkhtmltopdf, psycopg2, pytz…). This layer adds only what the addon needs on
# top: the Arabic fonts for PDF reports, the pip requirements, and a config file.
#
#   docker build -t dawrha/odoo:19 .
#   docker compose up -d          # compose builds this automatically
FROM odoo:19.0

# Root for the install steps; dropped back to `odoo` at the end.
USER root

# 1) Python dependencies (the "package.json" of the Odoo side). Kept minimal —
#    the addon uses only stdlib + packages already in the base image — but driven
#    from requirements.txt so adding one later is a one-line change + rebuild.
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    || pip3 install --no-cache-dir -r /tmp/requirements.txt

# 2) Arabic PDF rendering. wkhtmltopdf resolves fonts through fontconfig and the
#    base image ships no joined Arabic face, so printed names garble. Bake the
#    Noto Naskh Arabic fonts into the image and rebuild the font cache — this
#    survives rebuilds, unlike a mounted volume.
COPY addons/recycle_warehouse/static/src/fonts/ /usr/share/fonts/truetype/dawrha/
RUN fc-cache -f >/dev/null 2>&1 || true

# 3) Server configuration (addons path, db filter, workers, limits).
COPY odoo.conf /etc/odoo/odoo.conf
RUN chown odoo /etc/odoo/odoo.conf

# 4) The custom addon. Baked into the image for a reproducible, deployable
#    artifact. In local development the compose file overlays a bind-mount on the
#    same path so live edits still take effect without a rebuild.
COPY --chown=odoo:odoo addons/recycle_warehouse /mnt/extra-addons/recycle_warehouse

USER odoo
