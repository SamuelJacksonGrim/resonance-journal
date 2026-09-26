# Resonance Journal

A small, local-first journal for the terminal. Your entries live in one SQLite
file on your machine. Nothing is sent anywhere.

Create, edit, tag, link, search, view, archive, and export entries. Links show
up on both ends as backlinks, so you can follow how one thought resonates with
another.

- **No dependencies.** Python 3.10+ standard library only (tested on 3.10–3.13).
- **Private by default.** The journal file is `0600`, exports are `0600`, and
  the program has no network code (a test enforces this).
- **Nothing is lost silently.** There is no delete; `archive` hides an entry
  and can be undone. Export never overwrites without `--force`.

## Run it

```sh
# no install needed
python3 -m resonance_journal --help

# or install the `rj` command
pip install .
rj --help
```

The journal lives at `$RESONANCE_JOURNAL_DB`. If that is not set, it is
`$XDG_DATA_HOME/resonance-journal/journal.db` (default
`~/.local/share/resonance-journal/journal.db`). `--db PATH` overrides both.

## Use it

```sh
rj new "Low tide" --body "Walked out past the sandbar." -t sea -t walks
rj new "Night swim"                  # opens $VISUAL / $EDITOR (title line, blank line, body)
echo "Cold water." | rj new "Swim"   # body from stdin
rj edit 2                            # edit title+body in $EDITOR
rj edit 2 --title "Night swim, July" --body-file notes.txt

rj tag 2 sea moon                    # tags are normalized: "#Moon" == "moon"
rj untag 1 walks
rj tags                              # tag counts

rj link 2 1 --note "same beach"      # 2 → 1; 1 shows it as a backlink
rj unlink 2 1

rj show 1                            # full entry + links + backlinks
rj list                              # newest first (active entries)
rj search sandbar moon --tag sea     # every term must match (title, body, or tag)
rj list --archived                   # or --all

rj archive 1                         # hidden from list/search/export; reversible
rj unarchive 1

rj export --out journal-md                        # Markdown dir: index.md + one file per entry
rj export --all --format json --out journal.json  # lossless JSON (resonance-journal/v1)
rj export --out journal-md --force                # replace a previous export
```

Exit codes: `0` ok, `1` journal error (message on stderr), `2` usage error.

## Verify it

```sh
python3 -m unittest discover -s tests -t .   # 51 tests
./scripts/smoke.sh                           # end-to-end main path
```

## How it was built

This project was designed and built with the
[Architecture-Blueprints-Frameworks](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks)
method. Intent → construction pass → evidence → human decision.

- [`INTENT.md`](INTENT.md): what was asked, class `ui`, depth `standard`, and why
- [`architecture/`](architecture/): the ten artifacts. Start at
  [`architecture/README.md`](architecture/README.md)
- [`architecture/DecisionLog.md`](architecture/DecisionLog.md): why it is shaped
  this way (stack, no delete, export safety, ...)

```
resonance_journal/
  model.py     types, validators, errors, clock
  store.py     SQLite: the only code that opens the journal file
  service.py   use cases: the only authority on domain rules
  export.py    Markdown / JSON export: atomic, private, no silent overwrite
  cli.py       argument parsing, $EDITOR, rendering
tests/         unit, end-to-end, and import-boundary tests
scripts/smoke.sh
```
