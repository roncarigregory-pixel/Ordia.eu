#!/usr/bin/env bash
# Reinstalls a real Odoo 18 + PostgreSQL demo ERP for Bridge testing.
# System packages live in / which is ephemeral across pod restarts, so re-run this
# after a restart. /app (scripts) and MongoDB persist.
set -e
echo "[1/5] postgresql…"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-client >/dev/null 2>&1
service postgresql start
sleep 3
su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='odoo'\" | grep -q 1 || psql -c \"CREATE USER odoo WITH CREATEDB PASSWORD 'odoo';\"" || true
echo "[2/5] odoo repo + config…"
mkdir -p /etc/odoo
cat > /etc/odoo/odoo.conf <<'CONF'
[options]
admin_passwd = ordia_master
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
addons_path = /usr/lib/python3/dist-packages/odoo/addons
http_port = 8069
http_interface = 127.0.0.1
list_db = True
logfile = /tmp/odoo_run.log
CONF
curl -s https://nightly.odoo.com/odoo.key | gpg --dearmor -o /usr/share/keyrings/odoo-archive-keyring.gpg 2>/dev/null || true
echo "deb [signed-by=/usr/share/keyrings/odoo-archive-keyring.gpg] https://nightly.odoo.com/18.0/nightly/deb/ ./" > /etc/apt/sources.list.d/odoo.list
apt-get update -qq >/dev/null 2>&1
echo "[3/5] odoo install…"
DEBIAN_FRONTEND=noninteractive apt-get install -y odoo >/dev/null 2>&1
echo "[4/5] init db (sale_management + demo)…"
pkill -f odoo-bin 2>/dev/null || true; sleep 2
odoo -c /etc/odoo/odoo.conf -d ordia -i sale_management --stop-after-init >/tmp/odoo_init.log 2>&1 || cat /tmp/odoo_init.log
echo "[5/5] start server…"
(odoo -c /etc/odoo/odoo.conf -d ordia >/tmp/odoo_run.log 2>&1 &)
sleep 18
curl -s -m 10 -o /dev/null -w "odoo /web/login HTTP %{http_code}\n" http://localhost:8069/web/login
echo "DONE"
