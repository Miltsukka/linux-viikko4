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

### Measured server disk layout (17 November 2026)

Both VMs have an 80 GiB virtual disk (`/dev/vda`). `lsblk` reported:

| Device / mount | Server A (`linux-week1`) | Server B (`linux-week4`) |
|---|---|---|
| `/dev/vda` disk | 80G | 80G |
| `/dev/vda1`, `ext4`, mounted at `/` | 79G partition, 77G filesystem | 79G partition, 77G filesystem |
| `/dev/vda16`, `ext4`, mounted at `/boot` | 913M | 913M |
| `/dev/vda15`, `vfat`, mounted at `/boot/efi` | 106M | 106M |
| Root filesystem usage | 3.2G used, 74G available | 3.6G used, 73G available |

The web root and database live on each VM's root filesystem. B's backup directory is also on B's root filesystem, **not on a separately mounted backup disk**. However, the backups reside on a different VM from the original source, outside the public web root.

### Measured Linux users and file permissions

Values below are from `id` and `stat -c '%U:%G %a %n'` on 17 November 2026. Modes use octal notation (700 = owner-only; 600 = owner-only read/write; 755 = owner write and public read/traverse; 644 = owner write and public read).

| Server | Path | Owner:group | Mode | Purpose |
|---|---|---|---|---|
| A | `/var/www/html` | root:root | 755 | Website files and Week 3 report |
| A | `/var/lib/mysql` | mysql:mysql | 700 | MySQL data, restricted to owner |
| A | `/home/ubuntu/week4-backup.sh` | ubuntu:ubuntu | 700 | Backup script executable by owner |
| A | `/home/ubuntu/.ssh/id_ed25519_week4_backup` | ubuntu:ubuntu | 600 | Private SSH key, **never published** |
| B | `/var/www/html` | root:root | 755 | Nginx web root |
| B | `/var/lib/mysql` | mysql:mysql | 755 | MariaDB data; **check and tighten permissions to 700** |
| B | `/srv/backups/viikko4` | backupsvc:backupsvc | 700 | Non-public, owner-only backups |
| B | `/opt/viikko4` | root:root | 755 | Read-only app directory |
| B | `/opt/viikko4/app.py` | root:root | 644 | Flask source, writable by root |

Account identities:

- A: `ubuntu` (UID 1000; sudo-capable administration) and `mysql` (UID 109; database service).
- B: `ubuntu` (UID 1000), `mysql` (UID 109), `backupsvc` (UID 1001; SSH/rsync backup receiver), and `week4web` (UID 999; dedicated non-login application service).
- The B app uses local MariaDB account `week4web` with **SELECT only** on `viikko2.kayntilaskuri`; A uses a separate dedicated replication account for the source-to-replica connection.
- The private key is restricted on A. The B backup directory is `700`. The `backupsvc` home SSH folder and `authorized_keys` file should be checked with `sudo stat` before claiming their exact numeric modes (the initial unprivileged traversal did not show them).

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
