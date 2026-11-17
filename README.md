# Linux Administration – Weekly Assignment 4

**Server Cloning, Hourly Backups and Database Replication**

A coursework implementation using two CSC cPouta Ubuntu servers.

## Submitted pages

- **Server A (writer):** http://195.148.23.82/viikko2/
- **Server B (read-only replica):** http://128.214.254.249/viikko4/

## Architecture and cloning

- **A – `linux-week1`:** Ubuntu 24.04, MySQL 8.0.46, existing Week 2 Flask visitor counter and Week 3 report.
- **B – `linux-week4`:** Ubuntu 24.04, MariaDB 11.4.14 and a separate Week 4 read-only Flask app.
- B was created using a cPouta snapshot of A; each VM has its own private and public IP address.
- Their cloned Tailscale state was corrected so each VM has its own node identity. Tailscale is used for private inter-server transfers.
- B's old Week 2 writer service is not used by the Week 4 read-only page.

## Storage, backups and permissions

- A serves website files from `/var/www/html/`.
- An A-side cron job runs `/home/ubuntu/week4-backup.sh` at **minute 0 of every hour (UTC)**.
- The script copies A's website files with `rsync` over SSH to **B: `/srv/backups/viikko4/website-YYYY-MM-DD_HH-MM-SS/`**.
- Backups are timestamped, kept outside the public website and written by B's separate Linux account `backupsvc`. The backup directory and `authorized_keys` are restricted by ownership and permissions.
- A uses a dedicated SSH key for the backup transfer. **Private keys are not committed here.**
- Application and database credentials are not included in this repository.

### Successful backup runs (17 November 2026, UTC)

| Time | Execution | Result |
|---|---|---|
| 12:08:20 | Manual test | SUCCESS |
| 13:00:02 | Cron | SUCCESS |
| 14:00:02 | Cron | SUCCESS |

All three timestamped directories were listed on B. Further manual backup runs were successful at 14:34:20, 14:40:16 and 14:44:00 UTC. The last run copied files to B after its reboot.

### File restoration

From the 12:08 backup, `index.html` was restored into `/home/backupsvc/restore-test/`, separate from the live website. Its SHA256 checksum matched A's original:

`945f28abd1e648aef4297d3cd322ebbeb0811cdda264a9558dc000df69d48839`

## Database replication

- Source: **A / MySQL 8.0.46**, `viikko2.kayntilaskuri`.
- Replica: **B / MariaDB 11.4.14**, using a new MariaDB data directory and a SQL export from A.
- MySQL source uses row-based binary logging. B has a different `server_id`, `read_only=ON`, and `replicate-do-db=viikko2`.
- A uses a dedicated replication account restricted to B's Tailscale IP. Database traffic is bound to localhost and Tailscale, not the public network.
- A's MySQL 8 datadir was not reused directly by MariaDB.
- Replica source coordinates came from the consistent source export. Actual credentials and runtime `CHANGE MASTER TO` statements with passwords are not published.
- In this course setup, self-signed TLS certificate verification was disabled for the replication connection; production should validate the source certificate.
- B's Week 4 app uses the **`week4web`** Linux/database identity with `SELECT` only on the counter table. Its route performs a `SELECT` and does not issue updates.
- Replication is **not a substitute for historical backups**, because deletions and accidental modifications can replicate too.

## Verification

- B's local `/viikko4/` endpoint returned **HTTP 200**.
- B's counter stayed **27 → 27** after two loads of B's page.
- The replication connection was initially blocked by a self-signed certificate validation error; that issue was addressed, and the connection was reported working.
- **Post-reboot test (17 Nov 2026):** B booted at **14:28:01 UTC** (reported by `uptime -s`). After that, `nginx`, `mariadb`, `viikko4`, and `tailscaled` all reported **active**; the local B page returned **HTTP 200** and contained the GitHub repository link.
- **Post-reboot replication:** MariaDB reported `Slave_IO_Running: Yes`, `Slave_SQL_Running: Yes`, `Seconds_Behind_Master: 0`, with empty IO/SQL error fields.
- **Post-reboot backup transfer:** from A, `week4-backup.sh` returned `Backup completed successfully!` at 14:44 UTC, with the timestamped archive on B. A's `crontab -l` still contained the hourly schedule (`0 * * * *`).
- **Source-to-replica counter test passed (17 Nov 2026):** B's `SELECT kaynnit FROM viikko2.kayntilaskuri` showed **34**. Loading A's `/viikko2/` once and querying B again after 3 seconds showed **35**. This confirms A's update reached B without using B's page to write to the database. During peer assessment, repeating the same check should show the latest change.

## Main files

- [`backup/week4-backup.sh`](backup/week4-backup.sh): hourly rsync script
- [`backup/crontab.txt`](backup/crontab.txt): relevant cron entries
- [`config/source-mysql.cnf`](config/source-mysql.cnf): sanitised source configuration
- [`config/replica-mariadb.cnf`](config/replica-mariadb.cnf): sanitised replica configuration
- [`config/viikko4.service`](config/viikko4.service): systemd service
- [`config/nginx-week4-location.conf`](config/nginx-week4-location.conf): Nginx location snippet
- [`app/app.py`](app/app.py): B's read-only Flask application

## Problem solved / lessons learned

Cloning a VM also cloned its Tailscale device identity; separating those identities restored dependable private connectivity. Backups must be tested through an actual restore, and database replication must be checked independently from the website.

## Security

**Do not commit:** `*.sql`, `*.pem`, private SSH keys, passwords, environment files, backup archives, runtime logs, or complete unredacted database connection settings.
