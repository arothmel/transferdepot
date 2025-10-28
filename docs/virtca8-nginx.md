# virtca8 nginx bridge

This config (`deploy/virtca8-nginx.conf`) mirrors the original virtca8 nginx behaviour so legacy boxes on the Analysis LAN can reach both TransferDepot and MediaWiki through one front door.

## Layout
- Listens on `virtca8:80` (HTTP only).
- Serves TransferDepot via the local uWSGI socket at `/home/tux/transferdepot/run/transferdepot.sock`.
- Proxies `/wiki/` and `/index.php/...` to MediaWiki at `10.32.36.138` (upstream of Sh1re).
- Logs and pid go to `/home/tux/transferdepot/logs/` so everything stays inside this repo sandbox.

## Start
```bash
cd /home/tux/sh1re/transferdepot
mkdir -p logs
sudo nginx -c $(pwd)/deploy/virtca8-nginx.conf -p $(pwd)/
```

## Stop / reload
```bash
sudo nginx -s quit   -c $(pwd)/deploy/virtca8-nginx.conf -p $(pwd)/
# or reload if you change the config
sudo nginx -s reload -c $(pwd)/deploy/virtca8-nginx.conf -p $(pwd)/
```

## Test
- TransferDepot UI: `curl http://virtca8/admin/health`
- MediaWiki: `curl http://virtca8/index.php/Main_Page` (should be proxied to `10.32.36.138`).

Tail logs to confirm traffic paths:
```bash
sudo tail -f logs/virtca8-nginx.access.log logs/virtca8-nginx.error.log
```

Tune host headers inside the MediaWiki blocks if the upstream expects a named vhost (currently set to `10.32.36.138`).
