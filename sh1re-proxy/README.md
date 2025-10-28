# Pseudo Sh1re (DMZ proxy stand-in)

Goal: treat your existing `transferdepot` repo as the Analysis LAN host and use this directory as the Sh1re DMZ proxy. Run both on one laptop or split across VMs—it mirrors the production layout without touching the working app files.

## Emulate the UA IPs locally
Assign loopback aliases that match the addresses you use in UA:

```bash
sudo ip addr add 10.32.36.139/32 dev lo   # Sh1re DMZ proxy
sudo ip addr add 160.72.160.62/32 dev lo  # virtca8 (transferdepot backend)
# Optional: if you use a bridge host, add it too
# sudo ip addr add 10.32.36.141/32 dev lo
```

Remove them later with `sudo ip addr del <ip>/32 dev lo`.

Bind uwsgi to the virtca8 address so Sh1re can reach it:

```bash
uwsgi --ini uwsgi.ini --http-socket 160.72.160.62:8080
```

(`--http-socket` overrides the ini’s default 127.0.0.1 binding.)

## Layout
- `nginx.conf` – minimal reverse proxy listening on `:8081` and forwarding to the transferdepot HTTP listener at `127.0.0.1:8080` (the default uWSGI control socket).
- `sh1re-access.log`, `sh1re-error.log`, `sh1re-nginx.pid` – created when nginx runs so you can see request flow.

## Usage
1. Start the transferdepot backend exactly as you do today (bind uWSGI to `127.0.0.1:8080` or whichever port you expect).
2. In another terminal:
   ```bash
   cd /opt/sh1re-proxy            # adjust path to where you cloned this dir
   mkdir -p logs
   sudo nginx -c $(pwd)/nginx.conf -p $(pwd)/
   ```
3. Hit the pseudo Sh1re entry point: `curl http://10.32.36.139:8081/admin/health` or browse to `http://10.32.36.139:8081/<group>/`.
4. Tail logs here to prove traffic really lands on the proxy:
   ```bash
   tail -f logs/sh1re-access.log logs/sh1re-error.log
   ```

## Pointing at a remote backend
`upstream transferdepot_backend` points at the TransferDepot host (virtca8) and binds to `160.72.160.62:8080`, where uWSGI listens. Change this value only when uWSGI listens on a different host; set it to that host’s address and port so Sh1re continues to reach TransferDepot.
```nginx
 upstream transferdepot_backend {
    server 160.72.160.62:8080;
 }
```
Restart nginx (`sudo nginx -s reload -c $(pwd)/nginx.conf -p $(pwd)/`) and now the DMZ proxy talks across the subnet boundary while clients keep using the DMZ address.

## Shutdown / cleanup
- Stop Sh1re nginx: `sudo nginx -s quit -c $(pwd)/nginx.conf -p $(pwd)/`
- Remove runtime files if desired: `rm sh1re-access.log sh1re-error.log sh1re-nginx.pid`

This keeps the DMZ proxy logic isolated so you can experiment without risking the working transferdepot tree. Once satisfied, copy `nginx.conf` to the real Sh1re host and adjust only the upstream IP and TLS settings.
