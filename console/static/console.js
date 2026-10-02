/* LoomKart Ops Console. Talks to the FastAPI backend over SSE (fetch stream). */
"use strict";

const $ = (id) => document.getElementById(id);
const messagesEl = $("messages");
const toolsEl = $("tools");
const inputEl = $("input");
const sendEl = $("send");

let busy = false;
let stats = { questions: 0, calls: 0, tokensIn: 0, tokensOut: 0 };
const toolRows = new Map(); // name -> {root, dot, meta, args, calls, ms, errors}

/* ---------- boot ---------- */

fetch("/api/health")
  .then((r) => r.json())
  .then((h) => {
    $("model-chip").textContent = h.model.replace(/^global\.|^us\./, "");
    $("org-chip").textContent = `Zoho · ${String(h.dc).toUpperCase()}`;
    setConn(h.configured ? "up" : "down", h.configured ? "Connected" : "Not configured");
    sendEl.disabled = false;
  })
  .catch(() => setConn("down", "Backend offline"));

function setConn(state, text) {
  const conn = $("conn");
  conn.dataset.state = state;
  conn.querySelector(".dot").className = `dot dot-${state}`;
  conn.querySelector("span").textContent = text;
}

/* ---------- chat ---------- */

$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  ask(inputEl.value);
});

document.querySelectorAll(".suggest").forEach((btn) => {
  btn.addEventListener("click", () => ask(btn.dataset.q));
});

async function ask(question) {
  question = (question || "").trim();
  if (busy || !question) return;
  busy = true;
  sendEl.disabled = true;
  inputEl.value = "";
  const empty = $("empty");
  if (empty) empty.remove();

  let inner = messagesEl.querySelector(".inner");
  if (!inner) {
    inner = document.createElement("div");
    inner.className = "inner";
    messagesEl.appendChild(inner);
  }

  inner.appendChild(merchantBubble(question));
  const agentMsg = agentBubble();
  inner.appendChild(agentMsg);
  scrollBottom();

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question }),
    });
    if (!resp.ok || !resp.body) throw new Error(`backend returned ${resp.status}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep;
      while ((sep = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (frame.startsWith("data: ")) {
          handleEvent(JSON.parse(frame.slice(6)), agentMsg);
        }
      }
    }
  } catch (err) {
    appendError(agentMsg, "ConnectionError", String(err));
  } finally {
    const caret = agentMsg.querySelector(".caret");
    if (caret) caret.remove();
    busy = false;
    sendEl.disabled = false;
    inputEl.focus();
  }
}

function handleEvent(ev, agentMsg) {
  switch (ev.type) {
    case "token": {
      const textEl = agentMsg.querySelector(".msg-text");
      const raw = (agentMsg.dataset.raw || "") + ev.text;
      agentMsg.dataset.raw = raw;
      renderAnswer(textEl, raw);
      scrollBottom();
      break;
    }
    case "tool_start": {
      upsertToolRow(ev.name, ev.args, "run");
      break;
    }
    case "done": {
      const textEl = agentMsg.querySelector(".msg-text");
      agentMsg.dataset.raw = ev.answer;
      renderAnswer(textEl, ev.answer);
      for (const tool of ev.tools) {
        upsertToolRow(tool.name, null, "ok", tool);
      }
      stats.questions += 1;
      stats.calls += ev.stats.tool_calls;
      stats.tokensIn += ev.stats.tokens_in;
      stats.tokensOut += ev.stats.tokens_out;
      renderStats(ev.stats.avg_tool_ms);
      scrollBottom();
      break;
    }
    case "meta": {
      const head = agentMsg.querySelector(".msg-head .meta");
      if (head) head.textContent = `${(ev.duration_ms / 1000).toFixed(1)}s`;
      break;
    }
    case "error": {
      appendError(agentMsg, ev.error_type, ev.message);
      break;
    }
  }
}

/* ---------- message builders ---------- */

/* Renders the tiny markdown the model actually emits: **bold** only. Text is
   inserted as text nodes, so nothing from the model can become markup. */
function renderAnswer(el, raw) {
  el.textContent = "";
  for (const part of raw.split(/(\*\*[^*]+\*\*)/g)) {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      const strong = document.createElement("strong");
      strong.textContent = part.slice(2, -2);
      el.appendChild(strong);
    } else if (part) {
      el.appendChild(document.createTextNode(part));
    }
  }
}

function merchantBubble(text) {
  const wrap = document.createElement("div");
  wrap.className = "msg msg-merchant";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  return wrap;
}

function agentBubble() {
  const wrap = document.createElement("div");
  wrap.className = "msg msg-agent";
  const head = document.createElement("div");
  head.className = "msg-head";
  const label = document.createElement("span");
  label.textContent = "Agent";
  const meta = document.createElement("span");
  meta.className = "meta";
  head.append(label, meta);
  const text = document.createElement("div");
  text.className = "msg-text";
  const caret = document.createElement("i");
  caret.className = "caret";
  text.appendChild(caret);
  wrap.append(head, text);
  return wrap;
}

function appendError(agentMsg, type, message) {
  const box = document.createElement("div");
  box.className = "msg-error";
  const b = document.createElement("b");
  b.textContent = type;
  box.appendChild(b);
  box.appendChild(document.createTextNode("  " + message));
  agentMsg.appendChild(box);
  scrollBottom();
}

/* ---------- tool rail ---------- */

function upsertToolRow(name, args, state, aggregate) {
  let row = toolRows.get(name);
  if (!row) {
    $("tools-empty")?.remove();
    row = { calls: 0, ms: 0, errors: 0 };
    const root = document.createElement("div");
    root.className = "tool";
    const head = document.createElement("div");
    head.className = "tool-head";
    const dot = document.createElement("i");
    dot.className = "dot dot-run";
    const nameEl = document.createElement("span");
    nameEl.className = "tool-name";
    nameEl.textContent = name;
    const meta = document.createElement("span");
    meta.className = "tool-meta";
    meta.textContent = "running";
    head.append(dot, nameEl, meta);
    const argsEl = document.createElement("div");
    argsEl.className = "tool-args";
    root.append(head, argsEl);
    toolsEl.appendChild(root);
    row.root = root;
    row.dot = dot;
    row.meta = meta;
    row.argsEl = argsEl;
    toolRows.set(name, row);
  }

  if (args && Object.keys(args).length) {
    row.argsEl.textContent = "args " + compact(JSON.stringify(args));
  }
  if (state) row.dot.className = `dot dot-${state === "run" ? "run" : state}`;
  if (aggregate) {
    row.calls += aggregate.calls;
    row.ms += aggregate.duration_ms;
    row.errors += aggregate.errors;
    row.dot.className = "dot dot-ok";
    row.meta.textContent = `${row.calls} call${row.calls === 1 ? "" : "s"} · ${fmtMs(row.ms)}`;
  }
  $("tool-count").textContent = `${countTotalCalls()} calls`;
}

function countTotalCalls() {
  let total = 0;
  for (const row of toolRows.values()) total += row.calls;
  return total;
}

function compact(s) {
  s = s.replace(/\s+/g, " ");
  return s.length > 96 ? s.slice(0, 96) + "…" : s;
}

function fmtMs(ms) {
  return ms >= 1000 ? (ms / 1000).toFixed(1) + "s" : Math.round(ms) + "ms";
}

/* ---------- stats ---------- */

function renderStats(avgToolMs) {
  $("stat-questions").textContent = stats.questions;
  $("stat-calls").textContent = stats.calls;
  $("stat-tokens").textContent = `${stats.tokensIn} / ${stats.tokensOut}`;
  if (avgToolMs != null) $("stat-avg").textContent = fmtMs(avgToolMs);
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

inputEl.focus();
