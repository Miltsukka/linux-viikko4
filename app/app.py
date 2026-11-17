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
<section><h2>Backup and storage</h2>
<p>Both virtual machines use an 80 GB /dev/vda disk. The root filesystem is ext4 on /dev/vda1 (77G usable): A used 3.2G (74G free) and B used 3.6G (73G free) when checked on 17 Nov 2026. Each VM also has a 913M ext4 /boot partition and a 106M vfat /boot/efi partition.</p>
<p>Server A serves /var/www/html. Its backup script runs through cron every hour at minute 0 UTC and uses SSH + rsync to copy the web directory to B's /srv/backups/viikko4/website-YYYY-MM-DD_HH-MM-SS/. B stores backups on its root filesystem, outside the public web directory, on a separate VM from A. A's backup script records success and failure in a log.</p></section>
<section><h2>Linux users, owners and permissions</h2>
<p>A: /var/www/html root:root mode 755; /var/lib/mysql mysql:mysql mode 700; /home/ubuntu/week4-backup.sh ubuntu:ubuntu mode 700; dedicated backup private SSH key ubuntu:ubuntu mode 600.</p>
<p>B: /var/www/html root:root mode 755; /srv/backups/viikko4 backupsvc:backupsvc mode 700; /opt/viikko4 root:root mode 755; /opt/viikko4/app.py root:root mode 644. B's /var/lib/mysql was initially mode 755 and was then corrected to mysql:mysql mode 700 (verified with stat on 17 Nov 2026).</p>
<p>Linux accounts: ubuntu (administration) and mysql (database) exist on both machines; backupsvc (UID 1001) receives copies on B, and week4web (UID 999) runs B's Flask service. Database permissions are separate: B's week4web account has SELECT-only access to the replicated visitor counter. The A-to-B replication connection uses a dedicated database identity and restricted private-network access.</p>
<p>Mode 700 permits access only to the owner; mode 600 protects the private SSH key. Modes 755/644 allow read access where required for serving application code, while root retains write ownership.</p></section>
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
