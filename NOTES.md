# Notes

What building and playing this found, and what I asked the agent to change.

## The tests left four rules open, and I had to decide them

The test suite is the whole specification — there is no prose description of the
rules anywhere in the repo. Before writing any code I asked the agent to read
`tests/test_casino.py` and tell me what it required, and to flag anything it could
not determine from the tests alone. It came back with four genuine gaps:

1. **The exact capture rule.** The agent inferred "any non-empty subset of your
   hand whose values sum to the same total as any non-empty subset of the table".
   All three capture tests fit that, but none of them distinguishes it from the
   more traditional Cassino mechanic where one card sweeps up several same-rank
   cards. No test ever puts two same-rank cards on the table at once, so the case
   is untested.
2. **Building.** Traditional Cassino lets you combine a hand card with table cards
   into a build to capture later. There is no state field for it and `Move` only
   supports capture-or-place, so this variant appears to have no building.
3. **Placing on an empty table does not end your turn.** This was reverse-engineered
   from a single test about a sweep. The agent found two framings that both fit:
   "the empty table keeps your turn" and "a double move always follows a sweep".
4. **Tracking the last capturer.** Needed for who leads after a redeal and for the
   leftover cards at the end, but not in the documented state fields.

My decision was that the tests are the only authority: where they do not
distinguish between two readings, take the simplest one that makes all of them
pass, and do not go looking up the real rules of Hungarian Cassino to settle it.
So we went with the sums rule, no building, the empty-table framing, and an extra
internal field for the last capturer.

This is the part of the homework I did not expect. I assumed "make the tests pass"
was a mechanical instruction. It was not — the tests pin down most of the game and
leave real design choices open, and somebody has to make them.

## A bug the tests caught before I ever saw it

While making the tests pass, the "placing on an empty table keeps your turn" rule
turned out to be able to strand a player who had an empty hand with no legal move.
The one fixed-seed whole-deal test caught it. Fixed by never leaving the turn with
a player whose hand is empty while the other player still has cards.

## 1. The button that did nothing

**Playing:** I selected one card in my hand to place it and clicked "Play
selected". Nothing happened at all — the card stayed in my hand, the table did
not change, nothing appeared in the log. I tried a second card and got the same.

**Asked the agent:** told it exactly that, and added two things: check it in the
browser itself rather than only through the HTTP API, since it had told me it had
driven a whole deal through the API and clearly that path worked while clicking
did not; and when a selection is not legal, say so on screen instead of leaving
the button inert.

**Result:** fixed, and the cause was not what either of us assumed. The mechanics
were fine. What was broken was the feedback: the button was gated to enable only
for an exactly-legal selection, and a disabled button at 45% opacity looked lit
rather than off. A table card was still selected from an earlier click, so the
selection read as an illegal capture, and the button silently stayed dead. The
agent installed Playwright to drive a real browser and confirmed it there.

**What this taught me:** it was not a logic bug at all — it was the program
failing to tell me what it was doing. I could not distinguish "this move is
illegal" from "this button is broken", and that distinction is invisible to
whoever wrote the code and obvious to whoever is clicking.

## 2. The browser kept showing me the old version

**Playing:** after the agent reported the fix, the page behaved exactly as before.
A hard reload was what made the new version appear, twice over the session.

**Result:** not a bug in the game, but worth writing down: "the agent says it is
fixed" and "my browser is running the fixed version" are two different facts, and
I lost time assuming the first implied the second.

## 3. The server kept dying under me

**Playing:** the table went dead with "Safari can't connect to the server" several
times mid-session, each time while the agent was running its own checks.

**Result:** the agent and I were sharing one machine and one port, and its testing
kept killing the server I was playing on. I ended up giving the server its own
terminal and not touching it. Nothing to fix in the code — but it is a real cost
of having the agent verify on the same machine where I am using the thing.

## 4. The table was unplayable if you did not already know Cassino

**Playing:** this is the finding I did not expect to make. Nothing on screen said
what the cards were worth, that a capture means matching the sum of your selected
cards against the sum of the selected table cards, or that placing is the fallback.
I had to learn the rules from outside before I could use my own program. Everything
the agent built was correct and none of it was usable.

**Asked the agent:** add a short rules panel with the card values and the two
things you can do on a turn, show the value on each card, and — since the server
already computes `legal_moves` — show me the moves available right now, so I can
learn by looking instead of guessing.

**Result:** fixed. There is now a "How to play" panel, a value badge on every card
taken from `casino.value()` rather than duplicated in JavaScript, and a "Your
options this turn" list where clicking an option selects exactly those cards.

## 5. A final score I could not check

**Playing:** my first completed deal ended 0 cards to 52. Reading the log, I think
that is correct — I never once captured in that deal, so everything left on the
table went to the last capturer at the end, which was the computer. But from the
result screen alone I had no way to tell whether I had genuinely captured nothing
or the program was broken. The only evidence was the log, which was scrolled out
of view.

**Asked the agent:** show how many captures each side made during the deal, and
say explicitly when leftover table cards went to the last capturer at the end.

## What this taught me about working this way

The agent was far better than me at the part I expected to be hard — reading a
test suite as a specification, implementing the whole game, and getting fourteen
tests green — and much worse at the part I expected to be easy. Every problem I
found by playing was a problem of the program not communicating: a dead button
with no explanation, a table with no rules, a score with no way to check it. None
of those are visible from the code, and all of them are obvious within a minute of
actually using the thing.

The second lesson is about how it checks its own work. It told me a whole deal
worked because it had driven one through the HTTP API — a path no player uses. It
only found the real bug once it installed a browser and clicked the button itself.
That is the same failure I hit in the other half of this homework, where it
verified in Chrome while I was playing in Safari.