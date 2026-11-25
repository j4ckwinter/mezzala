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

## Releasing

Most players install the Claude Desktop extension, `mezzala.mcpb`, from the latest GitHub release. It is a `uv` bundle: Claude Desktop installs the dependencies from `pyproject.toml`, so the bundle carries only the source.

1. Raise `version` in both `pyproject.toml` and `manifest.json`. A test fails if they differ.
2. `npx @anthropic-ai/mcpb validate manifest.json && npx @anthropic-ai/mcpb pack . mezzala.mcpb` builds the bundle.
3. `gh release create v<version> mezzala.mcpb` publishes it. The asset must keep the name `mezzala.mcpb`, because the README links to the latest release's copy.

## Owners

| Decision | Owner |
| --- | --- |
| What a player and a snapshot hold | `src/mezzala/core/players.py` |
| Turning an fmsave record into a player, and what counts as unreadable | `src/mezzala/save/reader.py` |
| Reading the managed club's staff, first-team tactics and mentoring groups | `src/mezzala/save/own_club.py` |
| Reading each player's injury history, current injury and season stats | `src/mezzala/save/player_records.py` |
| Turning fmsave enum names into plain words | `src/mezzala/save/labels.py` |
| Nation names for FM's nation database ids. The save stores none, so `src/mezzala/data/nations.csv` names each id from the clubs the save lists for that nation | `src/mezzala/save/nations.py` |
| Which save sections may fail to read without failing the snapshot | `src/mezzala/save/sections.py` |
| Where FM27 keeps saves, and which one is used by default | `src/mezzala/save/saves.py` |
| When a new snapshot is taken, and which earlier snapshot a tool compares with | `src/mezzala/save/career.py` |
| How snapshots are stored | `src/mezzala/save/store.py` |
| How the watchlist is stored | `src/mezzala/save/watchlist.py` |
| How rejected players are stored | `src/mezzala/save/rejections.py` |
| Position groups, and when a player is natural or accomplished in one | `src/mezzala/core/positions.py` |
| Formations, how many starters each needs, the default formation, and which formation a saved tactic is | `src/mezzala/core/formations.py` |
| Who belongs to the club, who plays for it, what it pays them, depth, leaving dates, squad level | `src/mezzala/core/squad.py` |
| Choosing a starting eleven and its cover (a second eleven) for a formation | `src/mezzala/core/lineup.py` |
| Who is injured or banned on a given day | `src/mezzala/core/availability.py` |
| Nationality, and who needs no UK work permit | `src/mezzala/core/nationality.py` |
| A player's preferred foot and weak foot | `src/mezzala/core/feet.py` |
| FM roles: their key and preferable attributes, which foot suits them, and a player's role score | `src/mezzala/core/roles.py` |
| FM slot codes (DCL, WBR, AMC...): the position and side each stands for | `src/mezzala/core/shapes.py` |
| The assignment algorithm the eleven uses (Hungarian, minimum cost) | `src/mezzala/core/assignment.py` |
| Which players a club can realistically sign | `src/mezzala/core/reach.py` |
| Attribute profiles, how alike two players are, and the key attributes for each position | `src/mezzala/core/profile.py` |
| Projected and observed growth | `src/mezzala/core/growth.py` |
| Derived numbers: comparisons with similar players, league level, which release clause applies | `src/mezzala/core/metrics.py` |
| Which league a club is in, and how a league is named | `src/mezzala/core/leagues.py` |
| Money units and formatting | `src/mezzala/core/money.py` |
| What wage a player would expect: his own, or the going rate at clubs like yours | `src/mezzala/core/wages.py` |
| How a player is shown in answers | `src/mezzala/core/summary.py` |
| How ability is shown: CA and PA as numbers, or as stars in spoiler-free mode | `src/mezzala/core/view.py` |
| Finding a player by name | `src/mezzala/core/lookup.py` |
| Which players recruitment answers leave out because they were rejected | `src/mezzala/core/rejections.py` |
| Each tool's rules | `src/mezzala/tools/`, one module per tool |
| Tool names, parameters, defaults and errors | `src/mezzala/server.py` |
| How the Claude Desktop extension installs and starts mezzala | `manifest.json`, with `.mcpbignore` for what the bundle leaves out |

## Conventions

- Money is kept in the unit the save stores it in. `money.py` is the only place that converts it to pounds, in both directions.
- CA and PA are FM's hidden current and potential ability, from 1 to 200. Attributes run from 1 to 20.
- `uid` identifies a person within one save. FM can give a deleted person's `uid` to someone new, so matching across snapshots also checks the birth date (`is_same_person`).
- Stored snapshots encode each player as a positional list (`save/store.py`). Snapshots are history that cannot be rebuilt from the save, so a change to that encoding must keep existing rows readable: append new facts, add their defaults to `FACTS_ADDED_LATER`, and raise `CURRENT_FORMAT` so a snapshot in an older format is read again from the save.
- `core/` holds the football rules every tool shares, `tools/` one module per tool, and `save/` everything that reads saves or stores snapshots. `core/` and `tools/` take snapshots and return results; only `save/` and `server.py` touch fmsave, files, SQLite or MCP, and `core/` never imports from `tools/` or `save/`.
- Tests go through the MCP client (`tests/conftest.py`) with a fake save, so they pin behaviour, not internals.
- Anything shown to the manager that is CA, PA, or derived from them (averages, levels, gains) goes through `core/view.py` with the server's `View`. Under fog of war (`View.SPOILER_FREE`) they become stars, and hidden attributes and personality numbers stay out of answers; personality may still be described in words. `tests/test_fog_of_war.py` calls every tool, so a new tool that needs arguments gets an entry in its `ARGUMENTS`.
- Tools that take a formation accept none and resolve it with `with_formation` in `server.py`: the saved first-team tactic's shape, else `DEFAULT_FORMATION`, with a note in the answer when the tactic decided.

## Standards

- Each decision has one owner, listed above. Update the table in the same change that moves or adds one.
- Give every tuning number a name in the module that owns it.
- No comments unless they stop a plausible wrong fix. Tool docstrings are the published tool descriptions and stay.
- Add or update a test with every behaviour change, name it for the behaviour, and break the code once to see it fail.
- One logical change per commit, in Conventional Commits form. No AI attribution lines.

## Committing

Commit each completed change on `main` and push to the private GitHub repository. Making the repository public, publishing a package or a release, or changing Jack's Claude Code settings needs his request.
