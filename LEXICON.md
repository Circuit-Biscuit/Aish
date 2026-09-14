# Aish Lexicon — measured, not invented

Every row here was produced by `tools/aish.py lex` against `o200k_base`.
Regenerate any time: `python tools/aish.py lex <words...>`.

## The finding

**There is almost no abbreviation win available.** Modern BPE vocabularies
already contain the long technical words agents use. The intuitive move —
a big `cfg`/`impl`/`auth` shorthand table — buys **zero tokens** and costs
real clarity.

This table is short because the honest table *is* short.

## Approved (verified cheaper, still unambiguous)

| write this | instead of             | saves |
|------------|------------------------|-------|
| `^`        | prerequisite, requires | 2     |
| `ack`      | acknowledge            | 2     |
| `idem`     | idempotent             | 2     |
| `compat`   | backwards-compatible   | 2     |
| `->`       | therefore, leads to    | 1     |
| `async`    | asynchronous           | 1     |
| `race`     | race-condition         | 1     |
| `lat`      | latency                | 1     |

## Rejected — do NOT abbreviate these

Each already costs 1 token. Shortening them saves nothing and loses meaning:

> configuration, implementation, authentication, dependency, repository,
> parameter, deprecated, initialize, validation, serialization, migration,
> rollback, permission, environment, undefined, because, however, although,
> requires, depends, blocked, resolved, function

And these short forms are **not cheaper** than the full word — using them is
pure loss: `refac`, `repro`, `tput`, `idmp`, `nondet`, `prereq`, `deser`,
`uninit`, `flaky`.

## Rule

If a word is not in the approved table, **write it in full.** When in doubt,
measure. Do not guess, and do not grow this table from intuition — an
abbreviation that costs the same as the word it replaces is a pure loss.
