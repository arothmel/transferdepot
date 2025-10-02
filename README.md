# transferdepot
a file transfer service. We split it into three doors — a UI for people, an API for automation, and an Admin panel for health checks — and then moved file downloads out of the app entirely so they’re served directly by Nginx. That way, the app only does logic, and the web server does the heavy lifting for big transfers. 

## Todays Wins

  - Tuned Chunked Streaming: Dropped TD_CHUNK_SIZE to 1 MB and confirmed uWSGI reads nonstop without timing
  out; the 350 MB upload finally completed while the UI stayed responsive.
  - Heartbeat + Status Door: /group/status now shows “duration ≈ …”, manual clear, and retention-aware
  cleanup. /admin/health summarizes groups and live transfers; /admin/dev-api keeps the automation team
  happy.
  - Retention & Cleanup: Per-group retention (defaults/overrides) cleans both files and heartbeat JSON,
  surfaced via new env vars in app.py.
  - Packaging & Deploy: Replaced the zip with transferdepot-dev-pack.tar.gz, moved it across the air gap,
  unpacked on Virtca8, and proved the path end-to-end.
  - Proxy Resilience: Expanded Sh1re nginx timeouts and confirmed uWSGI socket/timeouts are aligned so
  stalled uploads don’t crash the box.

###  Next Tests

  1. Run the new 350 MB text upload (medium-big.txt) while tailing Sh1re/Virtca8 logs to verify no timeouts
  hit (collect timestamps for the network ticket).
  2. Try a smaller but choppy upload (intentionally pause the client mid-transfer) to confirm the heartbeat
  shovels updates and the connection survives.
  3. Exercise the “Clear completed entries” button on /group/status and ensure the admin health page reflects
  the cleanup.

