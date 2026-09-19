const SUIT_SYMBOL = { S: "♠", H: "♥", D: "♦", C: "♣" };
const RED_SUITS = new Set(["H", "D"]);

let selectedHand = new Set();
let selectedTable = new Set();
let latestState = null;

function cardParts(card) {
  const suit = card.slice(-1);
  const rank = card.slice(0, -1);
  return { rank, suit };
}

function cardLabel(card) {
  const { rank, suit } = cardParts(card);
  return `${rank}${SUIT_SYMBOL[suit] || suit}`;
}

function isRed(card) {
  return RED_SUITS.has(card.slice(-1));
}

function arraysEqual(a, b) {
  if (a.length !== b.length) return false;
  return a.every((v, i) => v === b[i]);
}

function currentSelectionIsLegal(state) {
  if (!state || selectedHand.size === 0) return false;
  const h = [...selectedHand].sort();
  const t = [...selectedTable].sort();
  return (state.legal_moves || []).some(
    (m) => arraysEqual(m.hand, h) && arraysEqual(m.table, t)
  );
}

function tableCardHasLegalMoveWith(state, card) {
  if (selectedHand.size === 0) {
    return (state.legal_moves || []).some((m) => m.table.includes(card));
  }
  const h = [...selectedHand].sort();
  return (state.legal_moves || []).some(
    (m) => arraysEqual(m.hand, h) && m.table.includes(card)
  );
}

// A plain-language reason for the current selection, so a disabled or about-
// to-fail "Play selected" is never just silently inert. Purely descriptive:
// it only reports what state.legal_moves (from the server) already says.
function selectionStatus(state) {
  if (!state || state.deal_over || state.player !== 0) return null;
  if (selectedHand.size === 0) {
    return selectedTable.size > 0
      ? { text: "Select one or more cards from your hand too.", kind: "info" }
      : null;
  }
  if (currentSelectionIsLegal(state)) {
    return selectedTable.size > 0
      ? { text: "Legal capture — click “Play selected”.", kind: "info" }
      : { text: "Legal placement — click “Play selected”.", kind: "info" };
  }
  if (selectedTable.size === 0) {
    return {
      text: "Not legal yet: to place, select exactly one card from your hand; to capture, also select table cards.",
      kind: "warn",
    };
  }
  return {
    text: "Not legal: your hand cards and the selected table cards don't add up to the same total. Clear the table selection to place a card instead.",
    kind: "warn",
  };
}

function makeCardEl(card, { clickable, selected, hint, value } = {}) {
  const el = document.createElement("div");
  el.className = "card" + (isRed(card) ? " red" : "");
  if (clickable) el.classList.add("clickable");
  if (selected) el.classList.add("selected");
  if (hint) el.classList.add("playable-hint");
  el.dataset.card = card;

  if (value !== undefined) {
    const badge = document.createElement("span");
    badge.className = "value-badge";
    badge.textContent = value;
    el.appendChild(badge);
  }
  const label = document.createElement("span");
  label.textContent = cardLabel(card);
  el.appendChild(label);
  return el;
}

function totalValue(cards, values) {
  return cards.reduce((sum, c) => sum + (values[c] || 0), 0);
}

// Describe one legal move in plain language, using the card values the
// server already computed (state.values) — no value arithmetic of our own.
function describeMove(move, values) {
  const handLabels = move.hand.map(cardLabel).join(" + ");
  if (move.table.length) {
    const tableLabels = move.table.map(cardLabel).join(" + ");
    const total = totalValue(move.hand, values);
    return `Capture ${tableLabels} using ${handLabels} (total ${total})`;
  }
  return `Place ${handLabels}`;
}

function renderOptions(state) {
  const list = document.getElementById("options-list");
  list.innerHTML = "";
  const isMyTurn = !state.deal_over && state.player === 0;

  if (!isMyTurn) {
    const li = document.createElement("li");
    li.id = "options-empty";
    li.textContent = state.deal_over ? "The deal is over." : "Waiting for the computer…";
    list.appendChild(li);
    return;
  }
  if (!state.legal_moves.length) {
    const li = document.createElement("li");
    li.id = "options-empty";
    li.textContent = "No legal moves.";
    list.appendChild(li);
    return;
  }

  const selHand = [...selectedHand].sort();
  const selTable = [...selectedTable].sort();
  const captures = state.legal_moves.filter((m) => m.table.length);
  const placements = state.legal_moves.filter((m) => !m.table.length);
  for (const move of [...captures, ...placements]) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "option-btn";
    btn.textContent = describeMove(move, state.values);
    if (arraysEqual(move.hand, selHand) && arraysEqual(move.table, selTable)) {
      btn.classList.add("chosen");
    }
    btn.addEventListener("click", () => {
      selectedHand = new Set(move.hand);
      selectedTable = new Set(move.table);
      render(latestState);
    });
    li.appendChild(btn);
    list.appendChild(li);
  }
}

function setMessage(text, kind) {
  const el = document.getElementById("message");
  el.textContent = text || "";
  el.className = kind === "info" ? "info" : kind === "warn" ? "warn" : "";
}

function render(state) {
  latestState = state;

  const isMyTurn = !state.deal_over && state.player === 0;
  const banner = document.getElementById("turn-banner");
  if (state.deal_over) {
    banner.textContent = "Deal over";
    banner.className = "";
  } else {
    banner.textContent = isMyTurn ? "Your turn" : "Computer's turn";
    banner.className = isMyTurn ? "mine" : "theirs";
  }

  document.getElementById("talon-count").textContent = state.talon_count;
  document.getElementById("sweeps-you").textContent = state.sweeps.you;
  document.getElementById("sweeps-computer").textContent = state.sweeps.computer;

  // Computer hand: face-down backs, one per card held.
  const compEl = document.getElementById("computer-hand");
  compEl.innerHTML = "";
  for (let i = 0; i < state.computer.hand_count; i++) {
    const back = document.createElement("div");
    back.className = "card-back";
    compEl.appendChild(back);
  }

  // Table.
  const tableEl = document.getElementById("table-cards");
  tableEl.innerHTML = "";
  for (const card of state.table) {
    const clickable = isMyTurn;
    const el = makeCardEl(card, {
      clickable,
      selected: selectedTable.has(card),
      hint: isMyTurn && tableCardHasLegalMoveWith(state, card),
      value: state.values[card],
    });
    if (clickable) {
      el.addEventListener("click", () => {
        if (selectedTable.has(card)) selectedTable.delete(card);
        else selectedTable.add(card);
        render(latestState);
      });
    }
    tableEl.appendChild(el);
  }

  // Player hand.
  const handEl = document.getElementById("player-hand");
  handEl.innerHTML = "";
  for (const card of state.you.hand) {
    const clickable = isMyTurn;
    const el = makeCardEl(card, {
      clickable,
      selected: selectedHand.has(card),
      value: state.values[card],
    });
    if (clickable) {
      el.addEventListener("click", () => {
        if (selectedHand.has(card)) selectedHand.delete(card);
        else selectedHand.add(card);
        render(latestState);
      });
    }
    handEl.appendChild(el);
  }

  document.getElementById("play-btn").disabled = !isMyTurn || selectedHand.size === 0;

  const status = selectionStatus(state);
  if (status) setMessage(status.text, status.kind);
  else if (isMyTurn) setMessage("");

  renderOptions(state);

  // Log.
  const logEl = document.getElementById("log");
  logEl.innerHTML = "";
  for (const line of state.log) {
    const li = document.createElement("li");
    li.textContent = line;
    logEl.appendChild(li);
  }
  logEl.scrollTop = logEl.scrollHeight;

  // Result overlay.
  const overlay = document.getElementById("result-overlay");
  if (state.deal_over && state.result) {
    overlay.classList.remove("hidden");
    fillResult(state.result);
  } else {
    overlay.classList.add("hidden");
  }
}

function fillResult(result) {
  const rows = [
    ["Captures made", result.captures.you, result.captures.computer, "captures"],
    ["Cards", result.breakdown.you.cards, result.breakdown.computer.cards],
    ["Spades", result.breakdown.you.spades, result.breakdown.computer.spades],
    ["Aces", result.breakdown.you.aces, result.breakdown.computer.aces],
    ["Big casino (10♦)", yesNo(result.breakdown.you.big_casino), yesNo(result.breakdown.computer.big_casino)],
    ["Little casino (2♠)", yesNo(result.breakdown.you.little_casino), yesNo(result.breakdown.computer.little_casino)],
    ["Sweeps", result.breakdown.you.sweeps, result.breakdown.computer.sweeps],
  ];
  const body = document.getElementById("result-body");
  body.innerHTML = "";
  for (const [label, you, comp, cls] of rows) {
    const tr = document.createElement("tr");
    if (cls) tr.className = cls;
    tr.innerHTML = `<td>${label}</td><td>${you}</td><td>${comp}</td>`;
    body.appendChild(tr);
  }
  const totalTr = document.createElement("tr");
  totalTr.className = "total";
  totalTr.innerHTML = `<td>Total score</td><td>${result.score.you}</td><td>${result.score.computer}</td>`;
  body.appendChild(totalTr);

  const title = document.getElementById("result-title");
  if (result.score.you > result.score.computer) title.textContent = "You win!";
  else if (result.score.you < result.score.computer) title.textContent = "Computer wins.";
  else title.textContent = "It's a tie.";

  const note = document.getElementById("result-leftover-note");
  if (result.leftover) {
    const cards = result.leftover.cards.map(cardLabel).join(", ");
    const who = result.leftover.recipient === "you" ? "you" : "the computer";
    note.textContent = `The deal ended with ${cards} still on the table and nobody left to play — those went to ${who}, as the last player to capture.`;
    note.classList.remove("hidden");
  } else {
    note.textContent = "";
    note.classList.add("hidden");
  }
}

function yesNo(b) { return b ? "Yes" : "No"; }

async function fetchState() {
  const res = await fetch("/api/state");
  const state = await res.json();
  render(state);
}

async function playSelected() {
  setMessage("");
  const body = JSON.stringify({ hand: [...selectedHand], table: [...selectedTable] });
  const res = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  const data = await res.json();
  if (!res.ok) {
    setMessage(data.error || "That move isn't legal.");
    return;
  }
  selectedHand.clear();
  selectedTable.clear();
  render(data);
}

async function newDeal() {
  selectedHand.clear();
  selectedTable.clear();
  setMessage("");
  const res = await fetch("/api/new", { method: "POST" });
  const data = await res.json();
  render(data);
}

document.getElementById("play-btn").addEventListener("click", playSelected);
document.getElementById("clear-btn").addEventListener("click", () => {
  selectedHand.clear();
  selectedTable.clear();
  render(latestState);
});
document.getElementById("new-deal-btn").addEventListener("click", newDeal);
document.getElementById("result-new-deal-btn").addEventListener("click", newDeal);

fetchState();
