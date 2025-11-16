# ONCALL PDF Validation Cron

Use `scripts/check_oncall_pdf.sh` to make sure the TransferDepot on-call board
stays healthy between refreshes. The script verifies both the PDF on disk and
the HTTP endpoint that serves it. Exit status is non-zero if either check
fails, so cron can alert you.

## Prerequisites
- `qpdf` and `curl` installed on the host (available via `dnf install qpdf curl`).
- The on-call PDF stored under `/home/tux/transferdepot-001/artifacts/ONCALL/oncall_board.pdf`.
- TransferDepot (or nginx) serving the PDF at `http://localhost/oncall/oncall_board.pdf`.

## Install
1. Copy the script onto the host (example assumes repo lives at `/home/tux/transferdepot`):
   ```bash
   install -m 0755 scripts/check_oncall_pdf.sh /home/tux/transferdepot-001/bin/check_oncall_pdf.sh
   ```
2. (Optional) override defaults via environment variables:
   - `TD_BASE_DIR` – base path (default `/home/tux/transferdepot-001`).
   - `TD_ONCALL_PDF` – full path to the PDF file.
   - `TD_ONCALL_URL` – URL curl should hit.
   - `TD_ONCALL_LOG` – log file path (default `${TD_BASE_DIR}/logs/oncall-check.log`).
   - `TD_ONCALL_CURL_TIMEOUT` – seconds curl waits before failing (default 10).

## Cron example
Add to the `tux` crontab (runs every 30 minutes):
```
*/30 * * * * /home/tux/transferdepot-001/bin/check_oncall_pdf.sh
```
This writes status lines to `/home/tux/transferdepot-001/logs/oncall-check.log`. Remove
stdout redirection if you want cron to mail failures instead.

## Manual run
Execute the script to verify everything works before handing it to cron:
```bash
TD_ONCALL_URL="http://transferdepot.sh1re.mycorp.ca/oncall/oncall_board.pdf" \
  /home/tux/transferdepot-001/bin/check_oncall_pdf.sh
```
Check the exit code (`$?`) and log file. A non-zero exit indicates either a
missing/corrupt PDF or an HTTP error (4xx/5xx/timeout).
