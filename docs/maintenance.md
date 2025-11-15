# TransferDepot Maintenance Checklist (virtca8)

## Daily (or before support demos)
- `systemctl status transferdepot.service` – confirm uWSGI is running.
- `curl -I http://virtca8:8080/admin/health` – verify the app responds.
- `curl -I http://virtca8/oncall/oncall_board.pdf` – confirm the ONCALL board loads.
- Review `/home/tux/transferdepot-001/logs/oncall-check.log` (cron-driven qpdf/curl test) to ensure the PDF stayed valid and reachable.

## Weekly
- `df -h /home/tux/transferdepot-001` – ensure the files/artifacts partition isn’t filling up.
- `ls -lh /home/tux/transferdepot-001/artifacts/ONCALL` – confirm the on-call PDF is updating; remove stale copies if needed.
- `journalctl -u transferdepot.service --since "1 week ago"` – skim for upload errors or crashes.

## After any config change
- `nginx -t` followed by `sudo systemctl reload nginx`.
- `sudo systemctl restart transferdepot.service` if app code changed.
- Smoke tests: upload a small file via `/SHIRE_GATEWAY`, download it, open `/admin/health`.

## Monthly
- Apply OS updates (`sudo dnf update`), then restart services.
- Archive old logs from `/home/tux/transferdepot/logs/` so the disk stays tidy.
- Verify SSL cert expiry if nginx is doing TLS (e.g., `openssl s_client -connect transferdepot.sh1re.mycorp.ca:443 -servername transferdepot.sh1re.mycorp.ca`).
