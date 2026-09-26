#!/usr/bin/env sh
# Smoke test: the main path exactly as a user would type it, against a
# throwaway journal. Exits non-zero on the first failure.
set -eu

cd "$(dirname "$0")/.."
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export RESONANCE_JOURNAL_DB="$WORK/journal.db"
rj() { python3 -m resonance_journal "$@" </dev/null; }
check() { printf '%s' "$1" | grep -q -- "$2" || { echo "FAIL: expected '$2' in:"; echo "$1"; exit 1; }; }

check "$(rj new 'Low tide' --body 'Walked out past the sandbar. Found a crab shell.' -t sea -t walks)" "created #1"
check "$(rj new 'Night swim' --body 'Cold water, bright moon.' -t Sea)" "created #2"
check "$(rj edit 2 --body 'Cold water, bright moon, loud surf.')" "saved #2"
check "$(rj tag 2 '#Moon')" "#moon"
check "$(rj untag 1 walks)" "#1 tags: #sea"
check "$(rj link 2 1 --note 'same beach')" "linked #2"
check "$(rj show 1)" "← 2  Night swim — same beach"
check "$(rj search SURF)" "Night swim"
check "$(rj search --tag sea)" "Low tide"
check "$(rj tags)" "2  #sea"
check "$(rj archive 1)" "archived #1"
out="$(rj list)"; printf '%s' "$out" | grep -q "Low tide" && { echo "FAIL: archived entry listed"; exit 1; }
check "$(rj list --archived)" "Low tide"
check "$(rj export --all --format json --out "$WORK/journal.json")" "exported 2 entries"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['format']=='resonance-journal/v1' and len(d['entries'])==2" "$WORK/journal.json"
check "$(rj export --all --out "$WORK/md")" "exported 2 entries"
test -f "$WORK/md/index.md" && test -f "$WORK/md/0001-low-tide.md"
if rj export --all --out "$WORK/md" 2>/dev/null; then echo "FAIL: export overwrote without --force"; exit 1; fi
check "$(rj unarchive 1)" "unarchived #1"
case "$(uname)" in
  MINGW*|MSYS*|CYGWIN*) ;;  # no POSIX modes
  *) check "$(ls -l "$RESONANCE_JOURNAL_DB")" "^-rw-------" ;;
esac
echo "smoke: OK (create, edit, tag, link, search, view, archive, export)"
