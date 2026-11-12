#!/usr/bin/env bash
# gates/10-no-secrets.sh: stop the run if the diff adds anything that looks like a secret or an env file.
if grep -qE '(^|/)\.env' <<<"$FACTORY_CHANGED"; then echo "The agents touched an .env file."; exit 1; fi
hits="$(git diff "$FACTORY_BASE" -- . | grep -E '^\+' | grep -nE '(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|(api[_-]?key|secret|token|password)\s*[:=]\s*["'"'"'][^"'"'"']{8,})' || true)"
if [ -n "$hits" ]; then echo "Possible secret in the diff:"; echo "$hits" | cut -c1-120; exit 1; fi
echo "No secrets found in the diff."
