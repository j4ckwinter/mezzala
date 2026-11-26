from mezzala.core.formations import DEFAULT_FORMATION
from mezzala.core.positions import ACCOMPLISHED_POSITION_RATING, NATURAL_POSITION_RATING
from mezzala.core.reach import REPUTATION_REACH
from mezzala.core.signing import PRE_CONTRACT_MONTHS
from mezzala.core.view import View
from mezzala.tools.risers import CA_BELOW_SQUAD_LEVEL, TARGET_MAX_AGE

INSTRUCTIONS = f"""\
mezzala reads the manager's Football Manager 27 save and answers squad, formation and transfer questions about it.
Every answer starts with the save's in-game date and club, and when the save file was written (save_written).
mezzala sees only what FM wrote at that save: budgets, transfers or squad changes made in the game since then do not
show until the manager saves again, so say so when an answer looks out of date. Each call checks the save file
and stores a new snapshot when it has changed, so growth compares real snapshots once there are two or more.
Money is in pounds. Fees are FM's transfer values, because asking prices are not stored in the save.
Current and potential ability (CA, PA) are FM's hidden 1-200 numbers.
find_players searches every player in the save with filters and sorts, and answers most recruitment
questions. shortlist builds a transfer shortlist within the budgets. wage_review, development_plan and
league_comparison cover wages, young players and how the squad compares with its league. squad lists
the players. compare_formations ranks formations by how well the squad fits them and shows each eleven.
what_changed, development_check, squad_progress and the watchlist tools (watch_player, unwatch_player,
watchlist) work from history and say so when there is only one snapshot. reject_player keeps a player who
has said no out of recruitment answers; unreject_player and rejected_players manage that list. next_job,
league_values and relegated_clubs cover managerial vacancies, the best-value leagues and clubs that dropped a league.
player_profile shows one player in full, or two side by side. training_plan suggests one of the club's players'
position, attribute focus, intensity, traits and mentors. dressing_room ranks captains and flags troublemakers.
fitness lists injuries, bans, injury risks, condition and sharpness. staff_review rates the backroom staff.
performance ranks season stats: who plays above or below their ability, finishing against xG, output per 90.
tactic_fit fits the squad to a custom shape given slot by slot with roles, scoring players by role.
squad_profile, positional_fit and next_opponent support tactics and match preparation; the save stores formations
but not roles or instructions, so suggest tactics from the attributes they report.
Positions are natural (FM rating {NATURAL_POSITION_RATING}+) or accomplished
({ACCOMPLISHED_POSITION_RATING}-{NATURAL_POSITION_RATING - 1}). Ask the manager which formation they
play if it matters. Tools that take one default to the shape of the first-team tactic saved in the game, even one
none of the formations match, and to {DEFAULT_FORMATION.value} when no saved tactic can be read; the notes say which."""

SPOILER_FREE_INSTRUCTIONS = """
Fog of war is on: the manager does not want to see what FM hides. Ability and potential come as star ratings
(5 stars is the best in the world), and hidden attributes and personality numbers are left out. Never state,
estimate or work back to CA or PA numbers, and talk about players the way FM's coaches and scouts would."""


def instructions_for(view: View) -> str:
    match view:
        case View.FULL:
            return INSTRUCTIONS
        case View.SPOILER_FREE:
            return INSTRUCTIONS + SPOILER_FREE_INSTRUCTIONS


RISERS_DESCRIPTION = f"""\
Players whose current ability is rising fastest.

scope: elsewhere (transfer targets), own (your players) or former (players who have left you, to spot
sales made too early). since is an in-game date; it defaults to the oldest snapshot. With one snapshot,
gains are projected rather than observed. max_fee is in pounds and defaults to the remaining transfer budget;
free agents always qualify. For elsewhere, min_ca defaults to {CA_BELOW_SQUAD_LEVEL} below the level of the current
first eleven and max_age to {TARGET_MAX_AGE}; for own and former there is no floor or age limit unless given."""

FIND_PLAYERS_DESCRIPTION = f"""\
Search every player in the save with filters and a sort. Money is in pounds (max_wage weekly).

Sorts: "value for money" puts players valued lowest against similar players first; "above league level"
puts players furthest above their league's first-team median CA first; "position attributes" ranks the
key attributes for the position (combine with max_ca to find attributes ahead of ability); "most
overpaid" ranks wages against similar players.

Who: scope "elsewhere" (default) searches other clubs and free agents, "own" your club, "everyone" the
whole save. position matches players natural or accomplished there (FM rating
{ACCOMPLISHED_POSITION_RATING} or more); natural_only keeps naturals ({NATURAL_POSITION_RATING} or more).
nationality matches a first or second nationality, such as "Republic of Ireland"; work_permit_free keeps
British and Irish players, who need no UK work permit. free_agents_only and clubs_only keep or leave out
players without a club.

Where: country is where the club plays (Cardiff count as England); division_level is 1 for a country's
top flight, estimated from first-team strength because the save names no leagues; league matches part
of a league's name, such as a club in it. reserves_only keeps players outside their club's first team;
bigger_clubs_only keeps clubs with a higher reputation than yours. within_reach keeps players whose
reputation is at most your club's plus {REPUTATION_REACH} (results show both), so a move is realistic
on paper, though a player may still refuse; set it false for questions like the best players in the world.

Availability: pre_contract_only keeps players whose contract ends within {PRE_CONTRACT_MONTHS} months, so you can
agree a pre-contract now; players on loan or at clubs in your own country often refuse one. The save does not
record transfer or loan listing; fringe_only keeps players whose
contract squad status says their club does not count on them (surplus to requirements, fringe player or
emergency backup), the likeliest to be listed or loaned.

Output: compact returns compact_players, one short row each (name, age, club, nationality, positions, ability,
potential, value, expected wage), instead of the full players list; use it for long searches.

Roles: role (an FM role such as "inside forward" or "ball-playing centre-back") adds each player's role score out
of 20 and allows sort "role fit"; side ("left" or "right") lets the score favour the foot the role wants there."""
