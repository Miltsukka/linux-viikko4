"""Read-only Week 4 visitor-counter app running on Server B."""
from flask import Flask, render_template_string
import pymysql

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Linux Administration Week 4</title>
<style>body{font-family:Arial,sans-serif;max-width:850px;margin:40px auto;padding:20px;background:#f4f6fa;color:#243047}
header{background:#25365c;color:white;padding:32px;border-radius:16px}section{background:white;padding:24px;margin-top:20px;border-radius:14px}
.count{font-size:56px;font-weight:bold;color:#2670ce}.tag{background:#e3f3e9;color:#176b41;padding:8px 12px;border-radius:20px}
a{color:#2670ce}</style></head><body>
<header><h1>Linux Administration – Week 4</h1><p>Server cloning, backups and database replication</p><p>Server B: linux-week4</p></header>
<section><h2>Replicated visitor counter</h2><p class="tag">Read-only replica</p><p>Visitor count from B's local database:</p><div class="count">{{ count }}</div><p>Reloading this page does not increment the counter.</p></section>
<section><h2>Server architecture</h2><p>A: Ubuntu 24.04 / MySQL 8.0.46; B: Ubuntu 24.04 / MariaDB 11.4.14.</p><p>B was cloned from A's cPouta snapshot. Separate addresses and Tailscale identities are used.</p></section>
<section><h2>Backup and storage</h2><p>A: /var/www/html; B: /srv/backups/viikko4; hourly cron with timestamped directories, stored outside the web root.</p></section>
<section><h2>Users and permissions</h2><p>Linux backupsvc receives SSH backups in restricted folders. The dedicated replication user is restricted to Server B's Tailscale address. The week4web account has SELECT-only access to the counter.</p></section>
<section><h2>Replication</h2><p>Row-based MySQL binary-log changes are replicated from A to B; B serves its local MariaDB copy in read-only mode. Replication does not replace historic backups because unintended changes replicate too.</p></section>
<section><h2>Test results</h2><p>Hourly backups: 17 Nov 2026 at 13:00 and 14:00 UTC succeeded. Restore: index.html SHA256 matched the original. B page local HTTP 200; two B page loads preserved counter 27 → 27.</p><p>Reboot test (17 Nov 2026): B restarted at 14:28:01 UTC. Nginx, MariaDB, the Week 4 app and Tailscale were active afterward. The local Week 4 endpoint returned HTTP 200 and included the GitHub link.</p><p>After reboot the replica reported IO: Yes, SQL: Yes and lag: 0 seconds, with no IO or SQL errors. A successful backup transfer to B was confirmed again at 14:44 UTC; A's hourly cron entry remained installed.</p><p>Source-to-replica update verified on 17 Nov 2026: B's local counter was 34; after one load of A's /viikko2/ page, B's local counter became 35 within 3 seconds. B does not increment its counter when loaded.</p></section>
<section><h2>Links</h2>
<p><a href="http://195.148.23.82/viikko2/">Server A: /viikko2/</a></p>
<p><a href="http://128.214.254.249/viikko4/">Server B: /viikko4/</a></p>
<p><a href="https://github.com/Miltsukka/linux-viikko4">GitHub repository and documentation</a></p>
</section></body></html>"""

@app.route("/viikko4/")
def week4():
    try:
        connection = pymysql.connect(
            unix_socket="/run/mysqld/mysqld.sock",
            user="week4web",
            database="viikko2",
            connect_timeout=5
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT kaynnit FROM kayntilaskuri ORDER BY id LIMIT 1")
                result = cursor.fetchone()
        finally:
            connection.close()
        if result is None:
            return "Visitor counter not found", 503
        return render_template_string(PAGE, count=result[0])
    except Exception:
        app.logger.exception("Database read failed")
        return "Database temporarily unavailable", 503
