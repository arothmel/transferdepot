# uWSGI quick checks

Use these steps to confirm the existing TransferDepot uWSGI process before you touch nginx.

## 1. Confirm the process and listener
```bash
ps -ef | grep uwsgi | grep -v grep
ss -lnpt 'sport = :8080'    # adjust the port if virtca8 listens elsewhere
```
Expect the uwsgi master PID and a listening socket such as `160.72.160.62:8080`.

## 2. Review recent log activity
```bash
tail -n20 run/uwsgi.log
```

## 3. Smoke test the health endpoint
```bash
curl -i http://142.63.160.62:8080/admin/health
```
You should see HTTP 200 and a new line in `run/uwsgi.log`. Run the curl from virtca8 if your jump host cannot reach the Analysis LAN IP directly.

---

The commands below are only needed when you must restart uWSGI manually.

## Optional: restart uWSGI
```bash
# add loopback alias when emulating locally
sudo ip addr add 160.72.160.62/32 dev lo

cd /opt/transferdepot
. .venv/bin/activate
uwsgi --ini uwsgi.ini \
      --http-socket 160.72.160.62:8080 \
      --daemonize run/uwsgi.log \
      --pidfile run/uwsgi.pid
```

Status checks after a restart:
```bash
ps -fp $(cat run/uwsgi.pid)
tail -f run/uwsgi.log
ss -lnpt 'sport = :8080'
```

Stop cleanly when required:
```bash
uwsgi --stop run/uwsgi.pid
```
(If the pid file is missing use `pkill -f "uwsgi.*transferdepot"` as a last resort.)

## Optional systemd unit template
```ini
[Unit]
Description=TransferDepot uWSGI
After=network.target

[Service]
WorkingDirectory=/opt/transferdepot
Environment=TD_UPLOAD_FOLDER=/opt/transferdepot/files
ExecStart=/opt/transferdepot/.venv/bin/uwsgi --ini /opt/transferdepot/uwsgi.ini --http-socket 160.72.160.62:8080
ExecStop=/opt/transferdepot/.venv/bin/uwsgi --stop /opt/transferdepot/run/uwsgi.pid
Restart=always
User=transferdepot
Group=transferdepot

[Install]
WantedBy=multi-user.target
```
Make sure `uwsgi.ini` (or the exec line) sets `--pidfile /opt/transferdepot/run/uwsgi.pid` so `ExecStop` works.
