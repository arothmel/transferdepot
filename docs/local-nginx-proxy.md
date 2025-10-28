# Local Nginx Reverse Proxy Walkthrough

Use this flow when you want to see transferdepot running the same way it does in UA, but all on your laptop. One host, one shell, and you can see each layer working.

## 0. Prereqs
- You are on a Linux machine with sudo.
- Nginx and uWSGI packages are available from your distro (Debian/Ubuntu commands shown, adapt as needed).
- This repo lives somewhere convenient like `/opt/transferdepot`.

```bash
sudo apt update
sudo apt install nginx python3-venv uwsgi uwsgi-plugin-python3
```

## 1. Start the Flask app via uWSGI
Run everything from the repo root so the bundled `uwsgi.ini` works out of the box.

```bash
cd /opt/transferdepot
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install flask werkzeug uwsgi
mkdir -p run/status files artifacts/ONCALL
uwsgi --ini uwsgi.ini
```

What to look for:
- uWSGI prints that it bound the Unix socket at `run/transferdepot.sock`.
- It also listens on `127.0.0.1:8080` (already defined in the ini) so you can sanity check without Nginx:
  ```bash
  curl http://127.0.0.1:8080/admin/health
  ```

Leave uWSGI running in this terminal. Open a second terminal for Nginx.

## 2. Add a local Nginx site definition
We keep the shipped production-ish config untouched. Instead, drop a minimal “playground” config that speaks HTTP to the existing 127.0.0.1:8080 endpoint, so you can see the full proxy flow without dealing with Unix socket wiring yet.

Create `/etc/nginx/sites-available/transferdepot-local` with the content below (substitute the repo path if different):

```nginx
# /etc/nginx/sites-available/transferdepot-local
server {
    listen 8081;                         # visit http://localhost:8081
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080; # uWSGI's built-in HTTP listener
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;             # keep uploads streaming
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Optional: fast health check, no buffering
    location = /healthz {
        proxy_pass http://127.0.0.1:8080/admin/health;
        proxy_buffering off;
        proxy_read_timeout 10s;
    }
}
```

Enable and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/transferdepot-local /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 3. Hit the app through Nginx
Now everything crosses the same layers you use in UA.

```bash
curl http://localhost:8081/admin/health
```

Example upload (replace with your own file and group):

```bash
curl -F group=BUFFER -F file=@/path/to/large-file.bin http://localhost:8081/upload
```

Watch progress the same way you would in UA:

- Browser: `http://localhost:8081/BUFFER/status`
- API: `curl http://localhost:8081/api/v1/groups/BUFFER/status | jq`

## 4. (Optional) Swap to Unix socket
Once the flow makes sense, flip the proxy to use the Unix socket so it matches the production layout more closely.

1. Change the `proxy_pass` block to:
   ```nginx
   location / {
       include uwsgi_params;
       uwsgi_pass unix:/opt/transferdepot/run/transferdepot.sock;
       uwsgi_read_timeout 3600s;
       uwsgi_send_timeout 3600s;
   }
   ```
2. Comment out the `http-socket` line in `uwsgi.ini` if you no longer want the 127.0.0.1:8080 listener.
3. Reload uWSGI (`Ctrl+C`, then rerun `uwsgi --ini uwsgi.ini`) and reload Nginx.

## 5. Tear-down / reset
- Stop uWSGI with `Ctrl+C`.
- Disable the local site if you want Nginx back to normal: `sudo rm /etc/nginx/sites-enabled/transferdepot-local && sudo systemctl reload nginx`.
- Remove the Python venv when you are done experimenting: `rm -rf /opt/transferdepot/.venv`.

## Mental model refresher
```
[Browser]
    ↓ HTTP
[Nginx :8081]
    ↓ proxy_pass http://127.0.0.1:8080 (or uwsgi_pass unix:...)
[uWSGI]
    ↓ WSGI call
[Flask app]
```

Walking through the layers one at a time keeps “which process is actually handling my upload?” crystal clear. Once this clicks locally, mirroring it on Virtca8 or any other host is just rerunning the same steps with the production paths.
