# Legacy client access to Shire

Use this checklist when you validate how legacy/analysis subnet stations (e.g. causer2) reach the DMZ Shire proxy. Keep "TD" as the placeholder for the upstream service name.

## 1. Host file entry (legacy style)
1. Log on to causer2 (OPS LAN) or another legacy workstation.
2. Inspect the hosts file entry instead of relying on DNS:
   ```bash
   grep sh1re /etc/hosts
   ```
   - Confirm `transferdepot.sh1re.mycorp.net` maps to Shire’s DMZ IP `10.32.36.139`.
   - If `sh1re.mycorp.net` is missing (common today), note it for follow-up.

## 2. Connectivity and routing
1. Because ICMP is blocked by policy, rely on the HTTP check in the next section and correlate with firewall logs to prove the path is open.

## 3. HTTP reachability tests
1. Use a browser on causer2 to open `http://transferdepot.sh1re.mycorp.net/healthz`. Confirm the page loads (no HTTPS on this network). Capture a screenshot for the ticket if needed.
2. Optional command-line check with tools available on RHEL6-era hosts (no curl or HTTPS required):
   ```bash
   wget --spider --server-response http://transferdepot.sh1re.mycorp.net/healthz
   ```
   - Expect an HTTP 200 or 302 in the server response headers.
3. Try the plain host to confirm the failure scenario (still HTTP only):
   ```bash
   wget --spider --server-response http://sh1re.mycorp.net/healthz
   ```
   - Log the error (e.g., “Name or service not known”) so you can justify adding an extra hosts entry or DNS record later.

## 4. Document the service path
Capture the effective route so the Operations and Analysis teams stay aligned:
- Legacy client → DNS resolves TD alias to Shire (10.32.36.139).
- Request crosses FW-2005 using the existing allow rule.
- Shire's nginx receives the HTTP request on 80/443 and forwards it upstream (TD placeholder).
- Response flows back to the legacy client through the same path.

Store the findings in the UA runbook and raise a follow-up if `sh1re.mycorp.net` needs to map to the same service (add an A/CNAME record or server_name alias in Shire's nginx).
