# Contributor instructions

mezzala is Jack Winter's MCP server for Football Manager 27. It reads a career save with [fmsave](https://github.com/rhiever/fmsave), keeps a snapshot each time the save changes, and answers transfer questions from those snapshots.

## Commands

Use Python 3.12 or newer. On Jack's Mac that is Homebrew's `python3.15`.

- `python3.15 -m venv .venv && .venv/bin/pip install -e ".[dev]"` installs.
- `.venv/bin/ruff format --check src tests && .venv/bin/ruff check src tests` lints and checks formatting.
- `.venv/bin/pyright` type-checks: strict for `src`, standard for `tests`.
- `.venv/bin/pytest -q` runs the tests.
- `.venv/bin/mezzala` runs the server over stdio. `--save` picks a save (default: the newest FM27 save) and `--database` picks where snapshots live (default `~/.mezzala/snapshots.db`).

Run all four checks before committing.

## Owners

| Decision | Owner |
| --- | --- |
| What a player and a snapshot hold | `src/mezzala/players.py` |
| Turning an fmsave record into a player, and what counts as unreadable | `src/mezzala/reader.py` |
| Where FM27 keeps saves, and which one is used by default | `src/mezzala/saves.py` |
| When a new snapshot is taken, and which earlier snapshot a tool compares with | `src/mezzala/career.py` |
| How snapshots are stored | `src/mezzala/store.py` |
| Position groups and when a player can play one | `src/mezzala/positions.py` |
| Formations and how many starters each needs | `src/mezzala/formations.py` |
| Who belongs to the club, who plays for it, depth, leaving dates, squad level | `src/mezzala/squad.py` |
| Choosing a starting eleven for a formation | `src/mezzala/lineup.py` |
| Which players a club can realistically sign | `src/mezzala/reach.py` |
| Attribute profiles and how alike two players are | `src/mezzala/profile.py` |
| Projected and observed growth | `src/mezzala/growth.py` |
| Money units and formatting | `src/mezzala/money.py` |
| How a player is shown in answers | `src/mezzala/summary.py` |
| Finding a player by name | `src/mezzala/lookup.py` |
| Each tool's rules | `src/mezzala/squad_list.py`, `squad_gaps.py`, `replacement.py`, `risers.py`, `sell_high.py`, `contract_watch.py`, `regen_intake.py` |
| Tool names, parameters, defaults and errors | `src/mezzala/server.py` |

## Conventions

- Money is kept in the unit the save stores it in. `money.py` is the only place that converts it to pounds, in both directions.
- CA and PA are FM's hidden current and potential ability, from 1 to 200. Attributes run from 1 to 20.
- `uid` identifies a person within one save. FM can give a deleted person's `uid` to someone new, so matching across snapshots also checks the birth date (`is_same_person`).
- Stored snapshots encode each player as a positional list (`store.py`). Snapshots are history that cannot be rebuilt from the save, so a change to that encoding must keep existing rows readable.
- The analysis modules take snapshots and return results. Only `reader.py`, `store.py`, `saves.py`, `career.py` and `server.py` touch fmsave, files, SQLite or MCP.
- Tests go through the MCP client (`tests/conftest.py`) with a fake save, so they pin behaviour, not internals.

## Standards

- Each decision has one owner, listed above. Update the table in the same change that moves or adds one.
- Give every tuning number a name in the module that owns it.
- No comments unless they stop a plausible wrong fix. Tool docstrings are the published tool descriptions and stay.
- Add or update a test with every behaviour change, name it for the behaviour, and break the code once to see it fail.
- One logical change per commit, in Conventional Commits form. No AI attribution lines.

## Committing

Commit each completed change on `main` and push to the private GitHub repository. Making the repository public, publishing a package or changing Jack's Claude Code settings needs his request.
