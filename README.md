# mezzala

i love football manager. i hate scrolling a 40,000-player search screen to find one decent centre back on a st mirren budget.
so i made an mcp server that reads my save and does the scouting for me. i ask claude, it asks mezzala, mezzala reads the save.

## what it answers

| tool | answers |
| --- | --- |
| `find_players` | searches the whole save: wonderkids under a price, undervalued players, players too good for their league, reserves stuck at bigger clubs, low release clauses, free agents, the best players in the world |
| `squad` | everyone available, loanees included, with natural and accomplished positions |
| `compare_formations` | which formation your squad fits best, with the eleven for each |
| `squad_gaps` | your eleven for a formation, plus where you're thin, ageing, losing players, weak, or have no young successor coming through |
| `find_replacement` | who plays like a player you're losing, fits your budget, and would actually sign |
| `risers` | who's improving fastest: transfer targets, your own players, or ones you sold too early |
| `sell_high` | which of your players to cash in on before their value drops |
| `contract_watch` | your contracts and loans running out, plus free agents and pre-contract targets who'd start for you |
| `regen_intake` | new regens since an earlier snapshot, best potential first |
| `snapshot` | reads the save now and lists the dates it has history for |

so you can ask things like:

- "find me the best wonderkids under £5m"
- "who's too good for the league they play in?"
- "who replaces gogić for under £1m?"
- "which of my players should i sell this window?"
- "anyone out of contract next summer who'd walk into my team?"
- "which of this year's regens are any good?"

## how it works

every call checks your save file. if it's changed, mezzala reads it with [fmsave](https://github.com/rhiever/fmsave) and keeps a snapshot for that in-game date. growth, falling values and new regens all come from comparing snapshots.

on day one there's only one snapshot, so `risers` projects next season's growth from age, the gap to potential, professionalism, determination and ambition. once you've saved later in the season it switches to real numbers. `regen_intake` needs a youth intake after your first snapshot before it has anything to show.

suggestions only include players whose reputation is close to your club's, so st mirren doesn't get told to sign benzema. pass `within_reach: false` if you want to dream.

## install it

you need python 3.12 or newer and football manager 27.

```sh
git clone https://github.com/j4ckwinter/mezzala.git
cd mezzala
python3 -m venv .venv
.venv/bin/pip install -e .
```

then add it to claude code:

```sh
claude mcp add --scope user mezzala -- "$PWD/.venv/bin/mezzala"
```

it reads your most recently saved fm27 career by default. to pin one, add `--save "/path/to/career.fm"` after the command. snapshots live in `~/.mezzala/snapshots.db`.

for the claude desktop app, add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (or settings → developer → edit config), then quit and reopen claude:

```json
"mcpServers": {
  "mezzala": { "command": "/full/path/to/mezzala/.venv/bin/mezzala", "args": [] }
}
```

both can run at once. they share the same snapshots, so after updating mezzala restart both: an older copy that's still running can't read snapshots a newer one wrote.

open a new claude code session, load your save in fm, and ask away. save in fm whenever you want mezzala to see what's changed.

## what it can't do

- fees are fm's transfer values. asking prices aren't in the save.
- it doesn't know your tactic. tell claude your formation (4-3-3, 4-2-3-1, 4-4-2, 4-4-2 diamond, 3-5-2 or 3-4-3) and it'll pass it along. the default is 4-3-3.
- `compare_formations` ranks shapes by how well your players fit them, not by how the match engine rates them. it treats wingers and wide midfielders as the same position, and full backs and wing backs too, so 4-1-4-1 and 5-3-2 would tie with 4-3-3 and 3-5-2.
- it sees everything, including hidden ca and pa. no fog of war.
- the save doesn't name leagues, and leagues that aren't loaded in your save don't count, so "above league level" only covers players in loaded leagues.
- a loan player counts at the club he's on loan to, so `reserves_only` and `bigger_clubs_only` don't find a big club's youngsters out on loan.
- fmsave has only verified fm27 build `27.0.0+2486695`. my save is on 27.1.1 and reads fine, but treat the numbers as fmsave's best effort.

## develop

```sh
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff format --check src tests && .venv/bin/ruff check src tests
.venv/bin/pyright
.venv/bin/pytest -q
```

[AGENTS.md](AGENTS.md) has the rest.
