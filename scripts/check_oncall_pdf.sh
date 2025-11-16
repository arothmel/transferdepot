#!/usr/bin/env bash
# Check that the on-call PDF is well-formed and the HTTP endpoint serves it.
set -euo pipefail

BASE_DIR="${TD_BASE_DIR:-/home/tux/transferdepot-001}"
PDF_PATH="${TD_ONCALL_PDF:-${BASE_DIR}/artifacts/ONCALL/oncall_board.pdf}"
ONCALL_URL="${TD_ONCALL_URL:-http://localhost/oncall/oncall_board.pdf}"
LOG_FILE="${TD_ONCALL_LOG:-${BASE_DIR}/logs/oncall-check.log}"
CURL_TIMEOUT="${TD_ONCALL_CURL_TIMEOUT:-10}"

mkdir -p "$(dirname "$LOG_FILE")"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  echo "$(timestamp) $1" | tee -a "$LOG_FILE"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "ERROR: required command '$cmd' not found in PATH"
    exit 2
  fi
}

require_command qpdf
require_command curl

status=0
log "Starting ONCALL PDF check (file: $PDF_PATH | url: $ONCALL_URL)"

if [[ ! -f "$PDF_PATH" ]]; then
  log "ERROR: PDF not found at $PDF_PATH"
  status=1
else
  if qpdf --check "$PDF_PATH" >/dev/null 2>&1; then
    log "OK: qpdf validation passed"
  else
    log "ERROR: qpdf validation FAILED"
    status=1
  fi
fi

if curl -Is --max-time "$CURL_TIMEOUT" "$ONCALL_URL" | head -n1 | grep -q '200'; then
  log "OK: HTTP endpoint responded with 200"
else
  log "ERROR: HTTP endpoint check FAILED"
  status=1
fi

if [[ $status -eq 0 ]]; then
  log "Completed ONCALL check successfully"
else
  log "Completed ONCALL check with errors"
fi

exit "$status"
