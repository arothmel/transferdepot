# UA verification checklist

Use this the next time you RDP/SSH into UA. It assumes TransferDepot already runs on virtca8 and Shire terminates HTTPS in the DMZ.

1. **Confirm uWSGI on virtca8**
   - `ps -ef | grep uwsgi | grep -v grep`
   - `ss -lnpt 'sport = :8080'`
   - `tail -n20 /home/tux/transferdepot/run/uwsgi.log`
   - `curl -i http://virtca8:8080/admin/health`

2. **Confirm virtca8 nginx**
   - `ps -ef | grep nginx | grep virtca8`
   - `sudo nginx -T | grep -A10 transferdepot` (spot-check the active config)
   - File to review: `/etc/nginx/nginx.conf` (expect TransferDepot blocks plus stubbed sections for Shire routing)
   - Tail logs if needed: `/var/log/nginx/transferdepot.access.log`, `/var/log/nginx/transferdepot.error.log`

3. **Review Shire (DMZ) proxy**
   - `ssh shire` (or jump via your usual path)
   - `ps -ef | grep nginx`
   - `sudo nginx -T | grep -A20 transferdepot`
   - `curl -k https://sh1re.mycorp.net/healthz`

4. **Cross-host tests**
   - From virtca8: `curl -i http://sh1re.mycorp.net/healthz`
   - From a legacy client: `curl -i http://virtca8/index.php/Main_Page`
   - From a modern client: `curl -k https://sh1re.mycorp.net/admin/health`

5. **File transfer sanity**
   - `curl -F group=BUFFER -F file=@/path/to/test.bin http://virtca8/upload`
   - Check `/home/tux/transferdepot/files/BUFFER/` for the file
   - Verify Shire proxy sees the request: tail its access log

6. **Cleanup (if you tested uploads)**
   - Remove any test artifacts from `/home/tux/transferdepot/files/`
   - Clear heartbeat files if needed: `/home/tux/transferdepot/run/status/BUFFER/`

Keep this checklist handy; adjust addresses/ports if UA changes.
