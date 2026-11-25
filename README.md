# mezzala

i love football manager. i hate scrolling a 40,000-player search screen to find one decent centre back on a st mirren budget.
so i made an mcp server that reads my save and does the scouting for me. i ask claude, it asks mezzala, mezzala reads the save.

## what it answers

| tool | answers |
| --- | --- |
| `find_players` | searches the whole save: wonderkids under a price, undervalued players, players too good for their league, reserves stuck at bigger clubs, low release clauses, free agents, the best players in the world |
| `squad` | everyone available, loanees included, with natural and accomplished positions |
| `compare_formations` | which formation your squad fits best, with the eleven for each |
| `shortlist` | a realistic shortlist, one target per weak position, within your transfer budget and wage room |
| `wage_review` | your wage bill, who's overpaid, and who could go without weakening the squad |
| `development_plan` | which youngsters are ready, who to loan out, and who to focus on |
| `league_comparison` | where your squad ranks in your league, overall and position by position |
| `what_changed` | what's changed since your last save: squad, budget, contracts, values, new regens, big transfers |
| `watch_player`, `watchlist` | mezzala's own shortlist, flagging targets that got cheaper |
| `development_check` | wonderkids who aren't developing as expected, and players in decline |
| `squad_progress` | your squad now against when you started using mezzala |
| `next_job` | open manager jobs, biggest club first, with each club's squad and money |
| `league_values` | which leagues have the cheapest players for their level |
| `relegated_clubs` | clubs that dropped a league since an earlier snapshot, and who's worth signing there |
| `squad_profile` | your eleven's attribute strengths and weaknesses against the league, for tactics |
| `positional_fit` | starters whose attributes suit another position better |
| `next_opponent` | your next opponent: likely shape, best eleven, key players, how they compare, recent form |
| `squad_gaps` | your eleven for a formation, plus where you're thin, ageing, losing players, weak, or have no young successor coming through |
| `find_replacement` | who plays like a player you're losing, fits your budget, and would actually sign |
| `risers` | who's improving fastest: transfer targets, your own players, or ones you sold too early |
| `sell_high` | which of your players to cash in on before their value drops |
| `contract_watch` | your contracts and loans running out, plus free agents and pre-contract targets who'd start for you |
| `regen_intake` | new regens since an earlier snapshot, best potential first, and which clubs produce them |
| `snapshot` | reads the save now and lists the dates it has history for |

so you can ask things like:

- "find me the best wonderkids under £5m"
- "who's too good for the league they play in?"
- "who replaces gogić for under £1m?"
- "which of my players should i sell this window?"
- "build me a shortlist within my budget"
- "how do we compare with the rest of the league?"
- "anyone out of contract next summer who'd walk into my team?"
- "which of this year's regens are any good?"

## how it works

every call checks your save file. if it's changed, mezzala reads it with [fmsave](https://github.com/rhiever/fmsave) and keeps a snapshot for that in-game date. growth, falling values and new regens all come from comparing snapshots.

on day one there's only one snapshot, so `risers` projects next season's growth from age, the gap to potential, professionalism, determination and ambition. once you've saved later in the season it switches to real numbers. `regen_intake` needs a youth intake after your first snapshot before it has anything to show.

suggestions only include players whose reputation is close to your club's, so st mirren doesn't get told to sign benzema. pass `within_reach: false` if you want to dream.

## install it

you need football manager 27 and [uv](https://docs.astral.sh/uv/). uv brings its own python, so you don't need one.

**1. get uv**, if you haven't already. on a mac or linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

on windows, in powershell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

then open a new terminal so it's on your path.

**2. install mezzala:**

```sh
uv tool install git+https://github.com/j4ckwinter/mezzala
```

**3. add it to claude.** for claude code on a mac or linux:

```sh
claude mcp add --scope user mezzala -- "$(uv tool dir --bin)/mezzala"
```

on windows, in powershell:

```powershell
claude mcp add --scope user mezzala -- "$(uv tool dir --bin)\mezzala.exe"
```

for the claude desktop app, run `uv tool dir --bin` to see where mezzala went. open settings → developer → edit config, and add mezzala to `mcpServers` with that folder's full path:

```json
{
  "mcpServers": {
    "mezzala": { "command": "/Users/you/.local/bin/mezzala" }
  }
}
```

on windows the command is `C:\\Users\\you\\.local\\bin\\mezzala.exe`, with doubled backslashes. if the file already has an `mcpServers` block, put the `mezzala` line inside it. then quit claude completely and reopen it. closing the window isn't enough.

**4. try it.** load your career in fm, save it, and ask claude "using mezzala, show me my squad". the first question reads the whole save, so give it a moment.

### which save it reads

mezzala reads whichever fm27 save was written most recently. it looks in fm's usual folders:

- mac: `~/Library/Application Support/Sports Interactive/Football Manager 27/games`
- windows: `Documents\Sports Interactive\Football Manager 27\games`, including a `Documents` folder that onedrive has moved

if your saves live somewhere else, or you want to stick to one career, pin it with `--save`. in claude code:

```sh
claude mcp add --scope user mezzala -- "$(uv tool dir --bin)/mezzala" --save "/path/to/career.fm"
```

in the desktop config, add `"args": ["--save", "/path/to/career.fm"]` next to `command`.

snapshots live in `~/.mezzala/snapshots.db`. save in fm whenever you want mezzala to see what's changed.

### update or remove it

```sh
uv tool upgrade mezzala
```

then restart claude code and the desktop app. both share the same snapshots, and an older copy that's still running can't read snapshots a newer one wrote.

to remove it: `claude mcp remove --scope user mezzala`, delete the `mezzala` entry from the desktop config, run `uv tool uninstall mezzala`, and delete `~/.mezzala` if you don't want your snapshots.

### if it doesn't work

- **claude doesn't list mezzala's tools.** run `claude mcp list` to see whether it connected. in the desktop app, check the command is a full path: the app doesn't use your terminal's path, so plain `mezzala` won't be found.
- **"no .fm saves found".** save your career in fm at least once, or pin the save with `--save`.
- **`uv` isn't found.** open a new terminal after installing it.

## what it can't do

- fees are fm's transfer values. asking prices aren't in the save.
- it can't read your tactic or roles, so tactical advice comes from your players' attributes.
- it doesn't know your formation. tell claude your formation (4-3-3, 4-2-3-1, 4-4-2, 4-4-2 diamond, 3-5-2 or 3-4-3) and it'll pass it along. the default is 4-3-3.
- `compare_formations` ranks shapes by how well your players fit them, not by how the match engine rates them. it treats wingers and wide midfielders as the same position, and full backs and wing backs too, so 4-1-4-1 and 5-3-2 would tie with 4-3-3 and 3-5-2.
- it sees everything, including hidden ca and pa. no fog of war.
- the save doesn't name leagues, and leagues that aren't loaded in your save don't count, so "above league level" only covers players in loaded leagues.
- a loan player counts at the club he's on loan to, so `reserves_only` and `bigger_clubs_only` don't find a big club's youngsters out on loan.
- fmsave has only verified fm27 build `27.0.0+2486695`. my save is on 27.1.1 and reads fine, but treat the numbers as fmsave's best effort.

## develop

you need python 3.12 or newer.

```sh
git clone https://github.com/j4ckwinter/mezzala.git
cd mezzala
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff format --check src tests && .venv/bin/ruff check src tests
.venv/bin/pyright
.venv/bin/pytest -q
```

to have claude run your checkout instead of the installed copy, point the command at `.venv/bin/mezzala`.
[AGENTS.md](AGENTS.md) has the rest.
