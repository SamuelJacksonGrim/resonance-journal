# System Flow — Resonance Journal

```
argv ─► parse (cli) ─► gather text (flag | file | stdin | $EDITOR)
                         │
                         ▼
               Journal.<verb>(...)            (service: validate + normalize)
                         │
                         ▼
          store: BEGIN ─► read/write ─► COMMIT (or ROLLBACK)
                         │
                         ▼
             Entry / [Entry] ─► render (cli)  ─► stdout, exit 0
                         │
                         └─► export.write(...) ─► files (0600), exit 0

 any JournalError ─► stderr "error: <message>", exit 1
 argparse error   ─► stderr usage,              exit 2
```
