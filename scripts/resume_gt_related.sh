#!/usr/bin/env bash
# Resume the Google Trends related-topics/queries extraction with backoff.
#
# `arboili gt-related` is resumable (progress lives in manifest_related.csv) and
# exits cleanly as soon as Google answers with HTTP 429. This wrapper re-invokes
# it until a run finishes without hitting 429, which means every
# (disease, geo, month, request_type) combination is done.
#
# SSL: this machine sits behind a TLS-inspecting proxy, so Python's bundled
# certifi store rejects Google with "self-signed certificate in certificate
# chain". We point OpenSSL at a keychain export (logs/ is gitignored, see the
# "local certs" entry in .gitignore) and rebuild it if it is missing.
#
# Usage:  scripts/resume_gt_related.sh        # from anywhere
# Log:    logs/gt-related.log (appended)

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG="$ROOT/logs/gt-related.log"
CA_BUNDLE="$ROOT/logs/macos-ca-bundle.pem"
INITIAL_BACKOFF=1800     # 30 min, grows on each 429
MAX_BACKOFF=21600        # 6 h cap
FAILURE_RETRY=300        # short wait before retrying a non-429 crash
MAX_FAILURES=10          # give up after this many consecutive crashes

# --- TLS trust store -------------------------------------------------------
if [ ! -s "$CA_BUNDLE" ]; then
  echo "===== building CA bundle from macOS keychains =====" | tee -a "$LOG"
  {
    security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain
    security find-certificate -a -p /Library/Keychains/System.keychain
  } > "$CA_BUNDLE" 2>/dev/null
fi
export SSL_CERT_FILE="$CA_BUNDLE"
export REQUESTS_CA_BUNDLE="$CA_BUNDLE"

# --- single-instance lock --------------------------------------------------
# Two concurrent runs would double-fetch the same requests and race on the
# read-merge-write of the output CSVs, so refuse to start a second one.
LOCK="$ROOT/logs/gt-related.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  oldpid="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [ -n "$oldpid" ] && kill -0 "$oldpid" 2>/dev/null; then
    echo "resume_gt_related is already running (pid $oldpid). Nothing to do."
    exit 1
  fi
  echo "Removing stale lock (pid ${oldpid:-unknown})."
  rm -rf "$LOCK"
  mkdir "$LOCK" || { echo "Cannot create lock $LOCK"; exit 1; }
fi
echo $$ > "$LOCK/pid"

backoff=$INITIAL_BACKOFF
failures=0
TMP="$(mktemp -t gt-related-run.XXXXXX)"
trap 'rm -f "$TMP"; rm -rf "$LOCK"' EXIT

echo "===== RESUME gt-related shell_pid=$$ $(date -u +%FT%TZ) ca=$CA_BUNDLE =====" | tee -a "$LOG"

while true; do
  echo "===== START gt-related $(date -u +%FT%TZ) =====" | tee -a "$LOG"

  # Stream live to the terminal and the log, while capturing this run's lines
  # so we can tell a 429 stop from a crash.
  before=$(wc -l < "$LOG")
  uv run arboili gt-related 2>&1 | tee -a "$LOG"
  status=${PIPESTATUS[0]}
  tail -n +"$((before + 1))" "$LOG" > "$TMP"

  if [ "$status" -ne 0 ]; then
    failures=$(( failures + 1 ))
    echo "===== gt-related exited $status (failure $failures/$MAX_FAILURES) — sleeping ${FAILURE_RETRY}s =====" | tee -a "$LOG"
    if [ "$failures" -ge "$MAX_FAILURES" ]; then
      echo "===== giving up after $MAX_FAILURES consecutive failures =====" | tee -a "$LOG"
      break
    fi
    sleep "$FAILURE_RETRY"
    continue
  fi

  failures=0

  if grep -q "Rate limit hit (429)" "$TMP"; then
    echo "===== 429 hit — sleeping ${backoff}s before resume ($(date -u +%FT%TZ)) =====" | tee -a "$LOG"
    sleep "$backoff"
    backoff=$(( backoff * 2 ))
    [ "$backoff" -gt "$MAX_BACKOFF" ] && backoff=$MAX_BACKOFF
    continue
  fi

  echo "===== gt-related finished without 429 $(date -u +%FT%TZ) =====" | tee -a "$LOG"
  break
done

echo "===== RESUME gt-related EXIT $(date -u +%FT%TZ) =====" | tee -a "$LOG"
echo
echo "Done. Press any key to close."
read -r -n 1
