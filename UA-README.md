# UA Morning Checklist

Bring this with you when you RDP into UA and jump to the shell. The goal is to confirm the running state without tearing anything down, prove nginx on virtca8 is actually serving traffic, and record gaps for the next build.

## 1. Hosts and roles
- **Shire (10.32.36.139)** – DMZ nginx reverse proxy, listens on 443 and forwards to `http://142.63.160.62:8080`.
- **virtca8 (142.63.160.62)** – TransferDepot app host: nginx listens on 80 and proxies to `/home/tux/transferdepot/run/transferdepot.sock`; uWSGI (using `uwsgi.ini`) serves the Flask app.
- **MediaWiki (10.32.36.138)** – upstream wiki service reachable through Shire.

Keep `/home/tux/transferdepot` as the working directory when you review configs on virtca8.

## 2. Confirm uWSGI is alive (virtca8)
1. List the process and listener:
   ```bash
   ps -ef | grep uwsgi | grep -v grep
   ss -lnpt 'sport = :8080'
   ```
   Expect the uwsgi master PID with a socket bound to `142.63.160.62:8080` (or whatever address is configured).
2. Inspect the log tail:
   ```bash
   tail -n20 /home/tux/transferdepot/run/uwsgi.log
   ```
3. Hit the health endpoint (from virtca8):
   ```bash
   curl -i http://142.63.160.62:8080/admin/health
   ```
   Should return HTTP 200 and append to the log tail.

## 3. Confirm nginx on virtca8 is in play
1. Check the master process:
   ```bash
   ps -ef | grep nginx | grep -v grep
   ```
2. Dump the active config and locate the TransferDepot blocks (watch for commented future Shire stubs):
   ```bash
   sudo nginx -T | grep -n "transferdepot" -A5
   ```
   Compare against `deploy/virtca8-nginx.conf` in this repo for the intended layout.
3. Tail logs to ensure requests are flowing:
   ```bash
   sudo tail -f /var/log/nginx/transferdepot.access.log /var/log/nginx/transferdepot.error.log
   ```
4. If time allows, browse `/etc/nginx/nginx.conf` to note any deviations or commented sections you want to address later.

## 4. Confirm Shire (DMZ) proxy
1. SSH to Shire and verify nginx:
   ```bash
   ps -ef | grep nginx | grep -v grep
   sudo nginx -T | grep -n "transferdepot" -A10
   ```
2. Hit Shire’s health endpoint (from virtca8 or a jump host):
   ```bash
   curl -k https://sh1re.mycorp.net/healthz
   ```
   Expect HTTP 200 routed through the proxy.

## 5. End-to-end smoke tests
- From a legacy-side shell (virtca8 is fine):
  ```bash
  curl -i http://virtca8/index.php/Main_Page         # MediaWiki via virtca8 nginx
  curl -F group=BUFFER -F file=@/tmp/test.bin http://virtca8/upload
  ```
  Confirm the upload lands in `/home/tux/transferdepot/files/BUFFER/` and shows up in the virtca8 nginx access log.
- From a “modern” vantage point (or curl with `-k`):
  ```bash
  curl -k https://sh1re.mycorp.net/admin/health
  ```

## 6. Capture findings before you leave
- Note any config drift between production and the `deploy/` or `sh1re-proxy/` references.
- Identify TODOs (e.g., commented Shire stubs inside virtca8’s nginx, missing documentation, firewall anomalies).
- Log timestamps of successful curl tests for future audits.
- Investigate any references to "virtca7" in Shire configs or runbooks to confirm whether an older proxy/middlebox influenced the current layout.

## 7. Reference material
- `deploy/virtca8-nginx.conf` – intended virtca8 nginx configuration.
- `docs/virtca8-nginx.md` – start/stop commands and log paths for virtca8 nginx.
- `sh1re-proxy/nginx.conf` + `sh1re-proxy/README.md` – DMZ proxy reference.
- `docs/uwsgi-start-stop.md` – quick checks and restart instructions (only if required).
- `docs/ua-verification-checklist.md` – detailed checklist shared with this README.
- `docs/legacy-client-path.md` – how legacy clients (e.g. causer2) reach Shire.

### Reminder
Tomorrow is reconnaissance. Do not restart uWSGI or nginx unless something is clearly broken. Use the commands above to prove what is running, and record any mismatches so the next build on this branch can address them.
