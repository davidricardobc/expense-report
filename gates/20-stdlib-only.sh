#!/usr/bin/env bash
# gates/20-stdlib-only.sh: this repo is standard-library only. Stop any new import outside it.
# Idea: a dependency is a human decision (Warp keeps humans on judgment calls), not an agent's.
added="$(git diff "$FACTORY_BASE" -- '*.py' | grep -E '^\+\s*(import|from)\s+[A-Za-z_]' || true)"
[ -z "$added" ] && { echo "No new imports."; exit 0; }
bad="$(printf '%s\n' "$added" | sed -E 's/^\+\s*(import|from)\s+([A-Za-z_][A-Za-z0-9_]*).*/\2/' | sort -u | python3 -c '
import sys
std = set(sys.stdlib_module_names) | {"report", "tests"}
print("\n".join(m for m in (l.strip() for l in sys.stdin) if m and m not in std))')"
if [ -n "$bad" ]; then
  echo "New import outside the standard library: $bad"
  echo "Adding a dependency is a human decision. Split the ticket or ask for approval."
  exit 1
fi
echo "All new imports are standard library."
