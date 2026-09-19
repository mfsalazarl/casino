"""Hungarian two-player Cassino.

Cards are strings: rank, then suit. Ranks A 2 3 4 5 6 7 8 9 10 J Q K,
suits S H D C.
"""
from typing import FrozenSet, NamedTuple, Optional, Tuple

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def value(card: str) -> int:
    return RANKS.index(card[:-1]) + 1


class Move(NamedTuple):
    hand: FrozenSet[str]
    table: FrozenSet[str]


class State(NamedTuple):
    hands: Tuple[Tuple[str, ...], Tuple[str, ...]]
    table: Tuple[str, ...]
    talon: Tuple[str, ...]
    piles: Tuple[Tuple[str, ...], Tuple[str, ...]]
    sweeps: Tuple[int, int]
    player: int
    last_capturer: Optional[int] = None


def new_deal(deck, first=0):
    deck = list(deck)
    other = 1 - first
    hands = [None, None]
    hands[first] = tuple(deck[0:3])
    hands[other] = tuple(deck[3:6])
    return State(
        hands=tuple(hands),
        table=tuple(deck[6:10]),
        talon=tuple(deck[10:]),
        piles=((), ()),
        sweeps=(0, 0),
        player=first,
        last_capturer=None,
    )


def _subset_sums(cards):
    """Map each achievable sum to the subsets (frozensets) of `cards` reaching it."""
    cards = list(cards)
    sums = {}
    for mask in range(1, 1 << len(cards)):
        subset = frozenset(c for i, c in enumerate(cards) if mask & (1 << i))
        total = sum(value(c) for c in subset)
        sums.setdefault(total, []).append(subset)
    return sums


def legal_moves(state):
    hand = state.hands[state.player]
    moves = {Move(frozenset({c}), frozenset()) for c in hand}

    hand_sums = _subset_sums(hand)
    table_sums = _subset_sums(state.table)
    for total, hand_subsets in hand_sums.items():
        for table_subset in table_sums.get(total, ()):
            for hand_subset in hand_subsets:
                moves.add(Move(hand_subset, table_subset))
    return moves


def play(state, move):
    if move not in legal_moves(state):
        raise ValueError(f"illegal move: {move!r}")

    player = state.player
    other = 1 - player

    hands = list(state.hands)
    hands[player] = tuple(c for c in state.hands[player] if c not in move.hand)

    piles = state.piles
    sweeps = state.sweeps
    last_capturer = state.last_capturer

    if move.table:
        table = tuple(c for c in state.table if c not in move.table)
        captured = tuple(move.hand) + tuple(move.table)
        piles = list(piles)
        piles[player] = piles[player] + captured
        piles = tuple(piles)
        last_capturer = player
        if not table:
            sweeps = list(sweeps)
            sweeps[player] += 1
            sweeps = tuple(sweeps)
        next_player = other
    else:
        turn_passes = len(state.table) != 0 or not hands[player]
        table = state.table + tuple(move.hand)
        next_player = other if turn_passes else player

    hands = tuple(hands)
    talon = state.talon

    if not hands[next_player] and hands[1 - next_player]:
        next_player = 1 - next_player

    if not hands[0] and not hands[1]:
        if len(talon) >= 6:
            leader = last_capturer if last_capturer is not None else player
            follower = 1 - leader
            new_hands = [None, None]
            new_hands[leader] = talon[0:3]
            new_hands[follower] = talon[3:6]
            hands = tuple(new_hands)
            talon = talon[6:]
            next_player = leader
        elif table and last_capturer is not None:
            piles = list(piles)
            piles[last_capturer] = piles[last_capturer] + table
            piles = tuple(piles)
            table = ()

    return State(
        hands=hands,
        table=table,
        talon=talon,
        piles=piles,
        sweeps=sweeps,
        player=next_player,
        last_capturer=last_capturer,
    )


def deal_over(state):
    return not state.hands[0] and not state.hands[1] and not state.table and not state.talon


def score(state):
    points = []
    for pile, swept in zip(state.piles, state.sweeps):
        pts = 0
        if len(pile) >= 27:
            pts += 3
        if sum(1 for c in pile if c.endswith("S")) >= 7:
            pts += 2
        pts += sum(1 for c in pile if c.startswith("A"))
        if "10D" in pile:
            pts += 2
        if "2S" in pile:
            pts += 1
        pts += swept
        points.append(pts)
    return tuple(points)
