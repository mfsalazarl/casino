"""A local browser table for playing one whole deal of Cassino against the
computer.

Run with: uv run web.py

All game rules come from casino.py. This file only ever calls value(),
new_deal(), legal_moves(), play(), deal_over() and score() from that module —
it does not decide, on its own, what is legal or how points are earned.
"""
import json
import random
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from casino import Move, deal_over, legal_moves, new_deal, play, score, value

HOST, PORT = "127.0.0.1", 8000
STATIC_DIR = Path(__file__).parent / "static"

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
ALL_CARDS = [r + s for s in "SHDC" for r in RANKS]

HUMAN, COMPUTER = 0, 1

game = {"state": None, "log": [], "captures": [0, 0], "leftover": None}


def computer_choice(state):
    """The computer captures the move taking the most table cards when it
    can, and otherwise places a random card from its hand."""
    moves = list(legal_moves(state))
    captures = [m for m in moves if m.table]
    if captures:
        return max(captures, key=lambda m: len(m.table))
    return random.choice([m for m in moves if not m.table])


def describe_move(player, move):
    who = "You" if player == HUMAN else "Computer"
    hand = ", ".join(sorted(move.hand))
    if move.table:
        table = ", ".join(sorted(move.table))
        return f"{who} played {hand} to capture {table}."
    return f"{who} placed {hand}."


def apply_move(state, move, player):
    """Play `move` for `player`, and record the bookkeeping the result
    screen needs: how many captures each side made, and — if this move ends
    the deal — which leftover table cards were swept to the last capturer,
    and who that was. All of that is read off the states play() returns
    (state.last_capturer) and the move itself, never re-decided here.
    """
    before = state
    state = play(before, move)

    if move.table:
        game["captures"][player] += 1

    if deal_over(state) and not deal_over(before):
        remaining = (set(before.table) - move.table) if move.table else (set(before.table) | move.hand)
        if remaining:
            game["leftover"] = {
                "cards": sorted(remaining),
                "recipient": "you" if state.last_capturer == HUMAN else "computer",
            }

    game["log"].append(describe_move(player, move))
    return state


def run_computer(state):
    while not deal_over(state) and state.player == COMPUTER:
        move = computer_choice(state)
        state = apply_move(state, move, COMPUTER)
    return state


def fresh_game():
    deck = list(ALL_CARDS)
    random.shuffle(deck)
    first = random.choice([HUMAN, COMPUTER])
    game["state"] = new_deal(deck, first=first)
    game["log"] = []
    game["captures"] = [0, 0]
    game["leftover"] = None
    game["state"] = run_computer(game["state"])


def explain_illegal(state, hand_cards, table_cards):
    if not hand_cards:
        return "Select at least one of your cards first."
    missing = sorted(c for c in hand_cards if c not in state.hands[state.player])
    if missing:
        return f"You don't hold {', '.join(missing)}."
    if table_cards:
        hv = sum(value(c) for c in hand_cards)
        tv = sum(value(c) for c in table_cards)
        if hv != tv:
            return f"Those don't add up: your cards total {hv}, the table cards total {tv}."
        return "That combination isn't available right now."
    if len(hand_cards) != 1:
        return "To place a card (without capturing), select exactly one card from your hand and no table cards."
    return "That's not a legal move right now."


def breakdown(state):
    out = {}
    for player, name in ((HUMAN, "you"), (COMPUTER, "computer")):
        pile = state.piles[player]
        out[name] = {
            "cards": len(pile),
            "spades": sum(1 for c in pile if c.endswith("S")),
            "aces": sum(1 for c in pile if c.startswith("A")),
            "big_casino": "10D" in pile,
            "little_casino": "2S" in pile,
            "sweeps": state.sweeps[player],
        }
    return out


def visible_state(state):
    finished = deal_over(state)
    visible_cards = set(state.hands[HUMAN]) | set(state.table)
    data = {
        "player": state.player,
        "you": {"hand": sorted(state.hands[HUMAN])},
        "computer": {"hand_count": len(state.hands[COMPUTER])},
        "table": sorted(state.table),
        "talon_count": len(state.talon),
        "sweeps": {"you": state.sweeps[HUMAN], "computer": state.sweeps[COMPUTER]},
        "deal_over": finished,
        "legal_moves": [],
        "values": {c: value(c) for c in visible_cards},
        "log": game["log"],
    }
    if not finished and state.player == HUMAN:
        data["legal_moves"] = [
            {"hand": sorted(m.hand), "table": sorted(m.table)} for m in legal_moves(state)
        ]
    if finished:
        points = score(state)
        data["result"] = {
            "score": {"you": points[HUMAN], "computer": points[COMPUTER]},
            "breakdown": breakdown(state),
            "captures": {"you": game["captures"][HUMAN], "computer": game["captures"][COMPUTER]},
            "leftover": game["leftover"],
        }
    return data


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        routes = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if self.path in routes:
            filename, content_type = routes[self.path]
            self._send_file(STATIC_DIR / filename, content_type)
        elif self.path == "/api/state":
            self._send_json(visible_state(game["state"]))
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {}

        if self.path == "/api/new":
            fresh_game()
            self._send_json(visible_state(game["state"]))
            return

        if self.path == "/api/move":
            state = game["state"]
            if state is None or deal_over(state):
                self._send_json({"error": "There's no deal in progress. Start a new one."}, 400)
                return
            if state.player != HUMAN:
                self._send_json({"error": "It's not your turn."}, 400)
                return

            hand_cards = frozenset(payload.get("hand", []))
            table_cards = frozenset(payload.get("table", []))
            move = Move(hand_cards, table_cards)
            try:
                state = apply_move(state, move, HUMAN)
            except ValueError:
                self._send_json({"error": explain_illegal(game["state"], hand_cards, table_cards)}, 400)
                return

            state = run_computer(state)
            game["state"] = state
            self._send_json(visible_state(state))
            return

        self.send_error(404)

    def log_message(self, format, *args):
        pass


def main():
    fresh_game()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Cassino is running at {url} (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
