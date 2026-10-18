#!/usr/bin/env python3
"""Build an interactive Family Feud hit/miss explorer (HTML + JSON + canvas sample)."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from score_benchmark import load_questions, match_score

ROOT = Path(__file__).resolve().parent
RESPONSES_PATH = ROOT / "responses" / "multi_provider_all_questions.json"
QUESTIONS_PATH = ROOT / "questions" / "all_questions.json"
OUT_HTML = ROOT / "responses" / "question_explorer.html"
OUT_JSON = ROOT / "responses" / "question_explorer_data.json"
OUT_CANVAS_SRC = ROOT / "responses" / "question_explorer.canvas.source.tsx"
ARTIFACT_HTML = Path("/opt/cursor/artifacts/family_feud_question_explorer.html")

# Exclude incomplete Google run from comparative views.
MODELS: list[tuple[str, str]] = [
    ("anthropic/claude-opus-4-6", "Opus"),
    ("fireworks/ember-1", "Ember"),
    ("fireworks/kimi-k3", "Kimi"),
    ("fireworks/qwen3p8-max", "Qwen"),
    ("openai/gpt-5.5", "GPT"),
]

TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("dating/sex", ("date", "dating", "sex", "sexy", "wife", "husband", "married", "boyfriend", "girlfriend", "kiss", "nude", "bedroom")),
    ("holiday/religion", ("christmas", "thanksgiving", "easter", "halloween", "church", "god", "pray", "religion", "holiday", "santa")),
    ("kids/school", ("kid", "kids", "child", "school", "teacher", "student", "homework", "classroom", "high school")),
    ("animals", ("dog", "cat", "pet", "animal", "horse", "bird", "fish", "zoo")),
    ("food", ("food", "eat", "restaurant", "cook", "kitchen", "breakfast", "dinner", "pizza", "burger")),
    ("sports", ("sport", "football", "baseball", "basketball", "soccer", "athlete", "olympics", "golf")),
    ("work/money", ("job", "boss", "work", "office", "money", "pay", "salary", "rich", "broke", "bank")),
    ("body", ("body", "hair", "teeth", "doctor", "hospital", "pregnant", "weight")),
    ("clothes", ("clothes", "wear", "dress", "shirt", "pants", "shoes", "fashion")),
    ("home", ("house", "home", "apartment", "living room", "bedroom", "bathroom", "furniture")),
    ("travel", ("travel", "vacation", "airport", "flight", "hotel", "car", "drive", "road")),
    ("entertainment", ("movie", "tv", "celebrity", "actor", "music", "concert", "hollywood", "hollywood")),
]


def topic_tags(question: str) -> list[str]:
    q = question.lower()
    hits = [name for name, keys in TOPIC_RULES if any(k in q for k in keys)]
    return hits or ["other"]


def entry_qa(item: dict[str, Any]) -> tuple[str, str]:
    if len(item) == 1:
        q, a = next(iter(item.items()))
        return str(q), str(a)
    return str(item.get("question", "")), str(item.get("response") or item.get("answer") or "")


def build_rows() -> dict[str, Any]:
    boards = load_questions(str(QUESTIONS_PATH))
    raw = json.loads(RESPONSES_PATH.read_text(encoding="utf-8"))

    by_model: dict[str, dict[str, str]] = {}
    for key, _label in MODELS:
        mapping: dict[str, str] = {}
        for item in raw.get(key, []):
            if not isinstance(item, dict) or not item:
                continue
            q, a = entry_qa(item)
            if q:
                mapping[q] = a
        by_model[key] = mapping

    questions = sorted(set.intersection(*(set(m.keys()) for m in by_model.values())))
    labels = [lab for _, lab in MODELS]

    miss_rows: list[list[Any]] = []
    disagree_rows: list[list[Any]] = []  # 1–2 hits
    hit_rows: list[list[Any]] = []
    solo_rows: dict[str, list[list[Any]]] = {lab: [] for lab in labels}
    model_miss_rows: dict[str, list[list[Any]]] = {lab: [] for lab in labels}
    unique_miss_rows: dict[str, list[list[Any]]] = {lab: [] for lab in labels}

    topic_n: Counter[str] = Counter()
    topic_miss: dict[str, list[int]] = defaultdict(lambda: [0] * len(MODELS))

    all_hit = all_miss = disagree = 0

    for q in questions:
        board_raw = boards.get(q, [])
        board = sorted(
            [
                [str(a.get("answer", "")), int(a.get("score") or 0)]
                for a in board_raw
                if a.get("answer")
            ],
            key=lambda pair: (-pair[1], pair[0].lower()),
        )
        answers = []
        pts = []
        matched: list[str | None] = []
        mask = 0
        for i, (key, _lab) in enumerate(MODELS):
            ans = by_model[key].get(q, "")
            score, matched_ans = match_score(ans, board_raw)
            answers.append(ans)
            pts.append(int(score))
            matched.append(matched_ans)
            if score > 0:
                mask |= 1 << i
        n_hits = bin(mask).count("1")
        tags = topic_tags(q)
        tag_str = ",".join(tags)
        # [question, topics, hitMask, modelAnswers, points, board[[ans,pts]], matchedBoardAns]
        row = [q, tag_str, mask, answers, pts, board, matched]

        for t in tags:
            topic_n[t] += 1
            for i in range(len(MODELS)):
                if (mask & (1 << i)) == 0:
                    topic_miss[t][i] += 1

        if n_hits == 0:
            all_miss += 1
            miss_rows.append(row)
        elif n_hits == len(MODELS):
            all_hit += 1
            hit_rows.append(row)
        else:
            disagree += 1
            if n_hits <= 2:
                disagree_rows.append(row)
            if n_hits == 1:
                for i, lab in enumerate(labels):
                    if mask & (1 << i):
                        solo_rows[lab].append(row)

        for i, lab in enumerate(labels):
            if (mask & (1 << i)) == 0:
                model_miss_rows[lab].append(row)
                if n_hits == len(MODELS) - 1:
                    unique_miss_rows[lab].append(row)

    # Prefer higher point gaps / surprising misses first for curated lists
    def sort_key(r: list[Any]) -> tuple:
        return (bin(r[2]).count("1"), -max(r[4]) if r[4] else 0, r[0])

    disagree_rows.sort(key=sort_key)
    for lab in labels:
        solo_rows[lab].sort(key=lambda r: (-max(r[4]), r[0]))
        unique_miss_rows[lab].sort(key=lambda r: (-max(r[4]), r[0]))
        # Cap list sizes in payload for miss-by-model (full in dedicated mode via mask filter)
        model_miss_rows[lab].sort(key=lambda r: (bin(r[2]).count("1"), -max(r[4]), r[0]))

    topic = {}
    for t, n in sorted(topic_n.items()):
        topic[t] = {
            "n": n,
            "miss": [round(topic_miss[t][i] / n, 3) if n else 0.0 for i in range(len(MODELS))],
        }

    # Compact: store full miss + disagree(<=2) + hit sample + solo samples + unique misses
    # For modelMiss mode, filter client-side from miss+disagree+hitSample is incomplete.
    # Instead embed a bitmask-filterable pool: all miss + all disagree-hard + sample of other disagrees
    # Better: embed `pool` of all non-unanimous-hit questions is huge.
    # Strategy: store miss (full), hardDisagree (1-2 hits full), solo (top 80 each),
    # uniqueMiss (top 80 each), and modelMissIndex as question indices into a shared `rows` pool.

    pool: list[list[Any]] = []
    seen: set[str] = set()

    def add_pool(rows: list[list[Any]], limit: int | None = None) -> None:
        for r in rows if limit is None else rows[:limit]:
            if r[0] in seen:
                continue
            seen.add(r[0])
            pool.append(r)

    add_pool(miss_rows)
    add_pool(disagree_rows)  # already only 1-2 hits
    # Also add remaining disagreements (3-4 hits) capped for browse
    mid = []
    for q in questions:
        # rebuild quickly from miss/disagree already added; scan again for 3-4 hit
        pass

    # Second pass for 3–4 hit disagreements (useful for "model unique miss")
    mid_rows: list[list[Any]] = []
    for lab_rows in unique_miss_rows.values():
        mid_rows.extend(lab_rows)
    mid_rows.sort(key=lambda r: (-max(r[4]), r[0]))
    add_pool(mid_rows, limit=2000)
    add_pool(hit_rows, limit=200)

    data = {
        "M": labels,
        "n": len(questions),
        "c": {
            "miss": all_miss,
            "hit": all_hit,
            "disagree": disagree,
            "solo": {lab: len(solo_rows[lab]) for lab in labels},
            "uniqueMiss": {lab: len(unique_miss_rows[lab]) for lab in labels},
        },
        "topic": topic,
        "miss": miss_rows,
        "disagree": disagree_rows,
        "hitSample": hit_rows[:150],
        "solo": {lab: solo_rows[lab][:80] for lab in labels},
        "uniqueMiss": {lab: unique_miss_rows[lab][:80] for lab in labels},
        # Full model-miss browse uses filters over miss+disagree+uniqueMiss pools in UI;
        # also expose counts for stats.
        "modelMissCount": {lab: len(model_miss_rows[lab]) for lab in labels},
    }
    return data


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Family Feud — Question hit/miss explorer</title>
<style>
  :root { color-scheme: dark light; --bg:#0f1115; --panel:#171a21; --line:#2a2f3a; --text:#e8eaed; --muted:#9aa3b2; --hit:#3d9a6a; --miss:#c45c5c; --accent:#6b8cff; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.45 ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
  header { padding:20px 24px 8px; max-width:1240px; margin:0 auto; }
  h1 { font-size:22px; margin:0 0 6px; font-weight:650; }
  .sub { color:var(--muted); margin:0 0 16px; max-width:72ch; }
  .stats { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; max-width:1240px; margin:0 auto 16px; padding:0 24px; }
  .stat { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; }
  .stat b { display:block; font-size:22px; }
  .stat span { color:var(--muted); font-size:12px; }
  .wrap { max-width:1240px; margin:0 auto; padding:0 24px 40px; display:grid; grid-template-columns: 1.05fr 0.95fr; gap:14px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; overflow:hidden; min-height:560px; display:flex; flex-direction:column; }
  .panel h2 { margin:0; padding:12px 14px; font-size:14px; border-bottom:1px solid var(--line); }
  .controls { display:flex; flex-wrap:wrap; gap:8px; padding:12px 24px; max-width:1240px; margin:0 auto; align-items:center; }
  select, input, button { background:#12151c; color:var(--text); border:1px solid var(--line); border-radius:8px; padding:8px 10px; }
  button { cursor:pointer; }
  button:disabled { opacity:.4; cursor:default; }
  .list { overflow:auto; flex:1; }
  .q { width:100%; text-align:left; border:0; border-bottom:1px solid var(--line); background:transparent; padding:10px 14px; color:inherit; cursor:pointer; }
  .q:hover, .q.active { background:#1d2230; }
  .q .t { font-weight:600; margin-bottom:4px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { font-size:11px; border:1px solid var(--line); border-radius:999px; padding:2px 8px; color:var(--muted); }
  .chip.on { color:var(--text); border-color:#445; background:#222733; }
  .pager { display:flex; gap:8px; align-items:center; padding:10px 12px; border-top:1px solid var(--line); color:var(--muted); }
  .detail { padding:14px; overflow:auto; }
  table { width:100%; border-collapse:collapse; }
  th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { color:var(--muted); font-weight:600; font-size:12px; }
  .hit { color:var(--hit); font-weight:650; }
  .miss { color:var(--miss); font-weight:650; }
  .topics { max-width:1240px; margin:0 auto 18px; padding:0 24px; }
  .topic-grid { display:grid; grid-template-columns: 160px repeat(5,1fr); gap:4px; font-size:12px; }
  .topic-grid div { padding:6px 8px; background:var(--panel); border:1px solid var(--line); }
  .topic-grid .h { color:var(--muted); font-weight:600; }
  .bar { height:8px; background:#222; border-radius:4px; overflow:hidden; margin-top:4px; }
  .bar > i { display:block; height:100%; background:var(--miss); opacity:.85; }
  .hint { color:var(--muted); font-size:12px; padding:0 24px 8px; max-width:1240px; margin:0 auto; }
  @media (max-width:900px){
    .wrap { grid-template-columns:1fr; }
    .stats { grid-template-columns:repeat(2,1fr); }
    .topic-grid { grid-template-columns: 120px repeat(2,1fr); }
  }
</style>
</head>
<body>
<header>
  <h1>Question hit / miss explorer</h1>
  <p class="sub">Click any question to see the survey board (correct answers), which models hit or missed, and each model’s raw answer. Soft-match scoring across Opus, Ember, Kimi, Qwen, and GPT on __N__ shared questions. Start with <b>All models wrong</b> to find unanimous misses.</p>
</header>
<div class="stats" id="stats"></div>
<div class="topics"><h2 style="font-size:14px;margin:0 0 8px;color:var(--muted)">Miss rate by topic (higher = harder for that model)</h2><div class="topic-grid" id="topics"></div></div>
<p class="hint">Tip: use <b>Only this model missed</b> to find blind spots unique to one model, or filter a topic like dating/sex to see where everyone struggles.</p>
<div class="controls">
  <select id="mode"></select>
  <select id="focus"></select>
  <select id="topic"></select>
  <input id="q" type="search" placeholder="Search question text…" style="min-width:220px;flex:1"/>
</div>
<div class="wrap">
  <div class="panel">
    <h2 id="listTitle">Questions</h2>
    <div class="list" id="list"></div>
    <div class="pager">
      <button id="prev" type="button">Prev</button>
      <span id="pageLabel"></span>
      <button id="next" type="button">Next</button>
    </div>
  </div>
  <div class="panel">
    <h2>Selected question</h2>
    <div class="detail" id="detail"></div>
  </div>
</div>
<script>
const DATA = __DATA__;
const M = DATA.M;
const pageSize = 40;
let mode = 'allMiss';
let focusModel = M[0];
let topic = 'all';
let query = '';
let page = 0;
let selected = null;

function nHits(mask){ let n=0; for(let i=0;i<M.length;i++) if(mask&(1<<i)) n++; return n; }
function hits(mask){ return M.filter((_,i)=> (mask&(1<<i))!==0); }
function misses(mask){ return M.filter((_,i)=> (mask&(1<<i))===0); }
function modelIndex(name){ return M.indexOf(name); }

function baseRows(){
  if(mode==='allMiss') return DATA.miss;
  if(mode==='hardDisagree') return DATA.disagree;
  if(mode==='allHitSample') return DATA.hitSample;
  if(mode==='solo') return DATA.solo[focusModel]||[];
  if(mode==='uniqueMiss') return DATA.uniqueMiss[focusModel]||[];
  if(mode==='modelMiss') {
    // Browse questions this model missed within miss + hard-disagree pools (+ unique miss extras)
    const idx = modelIndex(focusModel);
    const bit = 1 << idx;
    const seen = new Set();
    const out = [];
    for (const src of [DATA.miss, DATA.disagree, DATA.uniqueMiss[focusModel]||[]]) {
      for (const row of src) {
        if ((row[2] & bit) === 0 && !seen.has(row[0])) {
          seen.add(row[0]);
          out.push(row);
        }
      }
    }
    return out;
  }
  return [];
}

function filtered(){
  const q = query.trim().toLowerCase();
  return baseRows().filter(row=>{
    if(topic!=='all' && !row[1].split(',').includes(topic)) return false;
    if(q && !row[0].toLowerCase().includes(q)) return false;
    return true;
  });
}

function renderStats(){
  const c=DATA.c;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><b>${c.miss.toLocaleString()}</b><span>All models wrong</span></div>
    <div class="stat"><b>${c.disagree.toLocaleString()}</b><span>Models disagree</span></div>
    <div class="stat"><b>${c.hit.toLocaleString()}</b><span>All models right</span></div>
    <div class="stat"><b>${Object.values(c.solo).reduce((a,b)=>a+b,0).toLocaleString()}</b><span>Solo hits (any)</span></div>
    <div class="stat"><b>${Object.values(c.uniqueMiss||{}).reduce((a,b)=>a+b,0).toLocaleString()}</b><span>Unique misses (any)</span></div>`;
}

function renderTopics(){
  const el=document.getElementById('topics');
  const keys=Object.keys(DATA.topic);
  let html=`<div class="h">Topic</div>`+M.map(m=>`<div class="h">${m}</div>`).join('');
  for(const t of keys){
    const row=DATA.topic[t];
    html += `<div><b>${t}</b><div style="color:var(--muted)">n=${row.n}</div></div>`;
    for(let i=0;i<M.length;i++){
      const pct=Math.round(row.miss[i]*1000)/10;
      html += `<div>${pct}%<div class="bar"><i style="width:${pct}%"></i></div></div>`;
    }
  }
  el.innerHTML=html;
}

function renderControls(){
  const modeEl=document.getElementById('mode');
  modeEl.innerHTML=`
    <option value="allMiss">All models wrong (${DATA.c.miss})</option>
    <option value="hardDisagree">Hard disagreements — 1–2 hits (${DATA.disagree.length})</option>
    <option value="solo">Solo hits — only one model right</option>
    <option value="uniqueMiss">Only this model missed</option>
    <option value="modelMiss">This model missed (in hard sets)</option>
    <option value="allHitSample">All right sample (${DATA.hitSample.length})</option>`;
  modeEl.value=mode;

  const focusEl=document.getElementById('focus');
  const needsFocus = mode==='solo' || mode==='uniqueMiss' || mode==='modelMiss';
  focusEl.style.display = needsFocus ? '' : 'none';
  if(mode==='solo'){
    focusEl.innerHTML=M.map(m=>`<option value="${m}">${m} solo (${DATA.c.solo[m]||0})</option>`).join('');
  } else if(mode==='uniqueMiss'){
    focusEl.innerHTML=M.map(m=>`<option value="${m}">${m} unique miss (${(DATA.c.uniqueMiss||{})[m]||0})</option>`).join('');
  } else if(mode==='modelMiss'){
    focusEl.innerHTML=M.map(m=>`<option value="${m}">${m} misses (~${(DATA.modelMissCount||{})[m]||'?'})</option>`).join('');
  }
  focusEl.value=focusModel;

  const topicEl=document.getElementById('topic');
  topicEl.innerHTML=`<option value="all">All topics</option>`+Object.keys(DATA.topic).map(t=>`<option value="${t}">${t} (n=${DATA.topic[t].n})</option>`).join('');
  topicEl.value=topic;
}

function renderList(){
  const rows=filtered();
  const pageCount=Math.max(1, Math.ceil(rows.length/pageSize));
  if(page>pageCount-1) page=pageCount-1;
  const slice=rows.slice(page*pageSize, page*pageSize+pageSize);
  document.getElementById('listTitle').textContent=`Questions (${rows.length.toLocaleString()})`;
  document.getElementById('list').innerHTML = slice.map((row,idx)=>{
    const nh=nHits(row[2]);
    const active = selected && selected[0]===row[0];
    const chips=row[1].split(',').map(t=>`<span class="chip">${t}</span>`).join('');
    return `<button class="q ${active?'active':''}" data-i="${page*pageSize+idx}"><div class="t">${row[0].replace(/</g,'&lt;')}</div><div class="chips"><span class="chip on">${nh}/5 hit</span>${chips}</div></button>`;
  }).join('') || `<p style="padding:14px;color:var(--muted)">No questions match.</p>`;
  document.getElementById('pageLabel').textContent=`Page ${page+1} / ${pageCount}`;
  document.getElementById('prev').disabled=page<=0;
  document.getElementById('next').disabled=page>=pageCount-1;
  document.querySelectorAll('.q').forEach(btn=>{
    btn.onclick=()=>{
      const i=+btn.dataset.i;
      selected=filtered()[i];
      renderList();
      renderDetail();
    };
  });
}

function renderDetail(){
  const el=document.getElementById('detail');
  if(!selected){ el.innerHTML=`<p style="color:var(--muted)">Select a question to compare answers.</p>`; return; }
  const row=selected;
  const chips=row[1].split(',').map(t=>`<span class="chip on">${t}</span>`).join('');
  const board = row[5] || [];
  const matched = row[6] || [];
  let body=`<div style="font-weight:650;margin-bottom:8px">${row[0].replace(/</g,'&lt;')}</div>
    <div class="chips" style="margin-bottom:10px">${chips}</div>
    <div class="chips" style="margin-bottom:12px"><span class="chip on">Hits: ${hits(row[2]).join(', ')||'none'}</span><span class="chip">Misses: ${misses(row[2]).join(', ')||'none'}</span></div>
    <div style="font-weight:650;margin:4px 0 6px;font-size:13px">Survey board (correct answers)</div>
    <table style="margin-bottom:14px"><thead><tr><th>#</th><th>Answer</th><th>Pts</th></tr></thead><tbody>`;
  if(!board.length){
    body+=`<tr><td colspan="3" style="color:var(--muted)">No board answers found for this question.</td></tr>`;
  } else {
    board.forEach((pair, idx)=>{
      const ans = String(pair[0]||'').replace(/</g,'&lt;');
      body+=`<tr><td style="color:var(--muted)">${idx+1}</td><td>${ans}</td><td>${pair[1]}</td></tr>`;
    });
  }
  body+=`</tbody></table>
    <div style="font-weight:650;margin:4px 0 6px;font-size:13px">Model answers</div>
    <table><thead><tr><th>Model</th><th>Result</th><th>Answer</th><th>Matched board</th><th>Pts</th></tr></thead><tbody>`;
  for(let i=0;i<M.length;i++){
    const hit=(row[2]&(1<<i))!==0;
    const matchedAns = matched[i] ? String(matched[i]).replace(/</g,'&lt;') : '—';
    body+=`<tr><td>${M[i]}</td><td class="${hit?'hit':'miss'}">${hit?'HIT':'MISS'}</td><td>${(row[3][i]||'—').replace(/</g,'&lt;')}</td><td style="color:var(--muted)">${matchedAns}</td><td>${row[4][i]}</td></tr>`;
  }
  body+='</tbody></table>';
  el.innerHTML=body;
}

document.getElementById('mode').onchange=e=>{ mode=e.target.value; page=0; selected=null; renderControls(); renderList(); renderDetail(); };
document.getElementById('focus').onchange=e=>{ focusModel=e.target.value; page=0; selected=null; renderList(); renderDetail(); };
document.getElementById('topic').onchange=e=>{ topic=e.target.value; page=0; renderList(); };
document.getElementById('q').oninput=e=>{ query=e.target.value; page=0; renderList(); };
document.getElementById('prev').onclick=()=>{ page=Math.max(0,page-1); renderList(); };
document.getElementById('next').onclick=()=>{ page=page+1; renderList(); };

renderStats(); renderTopics(); renderControls(); renderList(); renderDetail();
</script>
</body>
</html>
"""


def canvas_source(data: dict[str, Any]) -> str:
    """Curated interactive canvas (size-safe sample of full HTML catalog)."""
    labels = data["M"]
    topic = data["topic"]

    def pick(rows: list, n: int) -> list:
        # diversify by topic
        by_t: dict[str, list] = defaultdict(list)
        for r in rows:
            by_t[r[1].split(",")[0]].append(r)
        out = []
        topics = list(by_t.keys())
        i = 0
        while len(out) < n and topics:
            t = topics[i % len(topics)]
            if by_t[t]:
                out.append(by_t[t].pop(0))
            else:
                topics = [x for x in topics if by_t[x]]
                if not topics:
                    break
                continue
            i += 1
        return out

    def trim_row(r: list[Any]) -> list[Any]:
        # Keep full model answers; cap board to top 6 for canvas size.
        board = (r[5] or [])[:6]
        return [r[0], r[1], r[2], r[3], r[4], board, r[6]]

    all_miss = [trim_row(r) for r in pick(data["miss"], 24)]
    hard = [trim_row(r) for r in pick(data["disagree"], 18)]
    solo = {
        lab: [trim_row(r) for r in (data["solo"].get(lab) or [])[:8]]
        for lab in labels
    }
    unique = {
        lab: [trim_row(r) for r in (data["uniqueMiss"].get(lab) or [])[:8]]
        for lab in labels
    }

    payload = {
        "M": labels,
        "c": data["c"],
        "topic": topic,
        "miss": all_miss,
        "hard": hard,
        "solo": solo,
        "uniqueMiss": unique,
    }
    # Embed as JSON literal
    blob = json.dumps(payload, ensure_ascii=False)

    return f'''import {{
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Select,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useMemo,
  useState,
}} from "cursor/canvas";

type BoardAns = [string, number];
type RowT = [string, string, number, string[], number[], BoardAns[], (string | null)[]];

const DATA = {blob} as {{
  M: string[];
  c: {{
    miss: number;
    hit: number;
    disagree: number;
    solo: Record<string, number>;
    uniqueMiss: Record<string, number>;
  }};
  topic: Record<string, {{ n: number; miss: number[] }}>;
  miss: RowT[];
  hard: RowT[];
  solo: Record<string, RowT[]>;
  uniqueMiss: Record<string, RowT[]>;
}};

const MODELS = DATA.M;

function nHits(mask: number): number {{
  let n = 0;
  for (let i = 0; i < MODELS.length; i++) if (mask & (1 << i)) n++;
  return n;
}}
function hitsFromMask(mask: number): string[] {{
  return MODELS.filter((_, i) => (mask & (1 << i)) !== 0);
}}
function missesFromMask(mask: number): string[] {{
  return MODELS.filter((_, i) => (mask & (1 << i)) === 0);
}}

type Mode = "allMiss" | "hard" | "solo" | "uniqueMiss";

export default function QuestionExplorer() {{
  const [mode, setMode] = useState<Mode>("allMiss");
  const [topic, setTopic] = useState("all");
  const [focusModel, setFocusModel] = useState<string>(MODELS[0]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<RowT | null>(DATA.miss[0] ?? null);
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const topicOptions = useMemo(() => {{
    const opts = [{{ value: "all", label: "All topics" }}];
    for (const t of Object.keys(DATA.topic)) {{
      opts.push({{ value: t, label: `${{t}} (n=${{DATA.topic[t].n}})` }});
    }}
    return opts;
  }}, []);

  const baseRows = useMemo(() => {{
    if (mode === "allMiss") return DATA.miss;
    if (mode === "hard") return DATA.hard;
    if (mode === "solo") return DATA.solo[focusModel] || [];
    return DATA.uniqueMiss[focusModel] || [];
  }}, [mode, focusModel]);

  const filtered = useMemo(() => {{
    const q = query.trim().toLowerCase();
    return baseRows.filter((row) => {{
      if (topic !== "all" && !row[1].split(",").includes(topic)) return false;
      if (q && !row[0].toLowerCase().includes(q)) return false;
      return true;
    }});
  }}, [baseRows, topic, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageSafe = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(pageSafe * pageSize, pageSafe * pageSize + pageSize);

  const topicCategories = Object.keys(DATA.topic);
  const topicSeries = MODELS.map((name, i) => ({{
    name,
    data: topicCategories.map((t) => Math.round(DATA.topic[t].miss[i] * 1000) / 10),
  }}));

  const hardestTopics = [...topicCategories]
    .map((t) => ({{
      t,
      avg: DATA.topic[t].miss.reduce((a, b) => a + b, 0) / MODELS.length,
    }}))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 3);

  return (
    <Stack gap={{20}} style={{{{ padding: 24, maxWidth: 1200 }}}}>
      <Stack gap={{6}}>
        <H1>Question hit / miss explorer</H1>
        <Text tone="secondary">
          Click a question to compare Opus, Ember, Kimi, Qwen, and GPT. Soft-match
          scoring on {{DATA.c.miss + DATA.c.hit + DATA.c.disagree}} shared questions.
        </Text>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat value={{String(DATA.c.miss)}} label="All models wrong" tone="danger" />
        <Stat value={{String(DATA.c.disagree)}} label="Models disagree" />
        <Stat value={{String(DATA.c.hit)}} label="All models right" tone="success" />
        <Stat
          value={{String(Object.values(DATA.c.solo).reduce((a, b) => a + b, 0))}}
          label="Solo hits"
        />
      </Grid>

      <Callout tone="warning" title="Full catalog in HTML">
        This canvas is a topic-diverse sample. Browse all {{DATA.c.miss}} unanimous
        misses and hard disagreements in responses/question_explorer.html (also
        /opt/cursor/artifacts/family_feud_question_explorer.html).
      </Callout>

      <Stack gap={{8}}>
        <H2>Hardest topics (avg miss rate)</H2>
        <Table
          headers={{["Topic", "Avg miss %", "n"]}}
          columnAlign={{["left", "right", "right"]}}
          rows={{hardestTopics.map(({{ t, avg }}) => [
            t,
            String(Math.round(avg * 1000) / 10),
            String(DATA.topic[t].n),
          ])}}
        />
      </Stack>

      <Stack gap={{8}}>
        <H2>Miss rate by topic</H2>
        <Text tone="secondary" size="small">
          Keyword tags · dating/sex and holiday/religion lead; Qwen is highest in
          both bands
        </Text>
        <BarChart
          height={{300}}
          categories={{topicCategories}}
          series={{topicSeries}}
          valueSuffix="%"
          yMax={{60}}
        />
      </Stack>

      <Divider />

      <Stack gap={{10}}>
        <H2>Inspect questions</H2>
        <Row gap={{10}} wrap>
          <Select
            value={{mode}}
            onChange={{(v) => {{
              setMode(v as Mode);
              setPage(0);
              setSelected(null);
            }}}}
            options={{[
              {{
                value: "allMiss",
                label: `All wrong sample (${{DATA.miss.length}} of ${{DATA.c.miss}})`,
              }},
              {{
                value: "hard",
                label: `Hard disagreements (${{DATA.hard.length}} sample)`,
              }},
              {{ value: "solo", label: "Solo hits (only one model right)" }},
              {{ value: "uniqueMiss", label: "Only this model missed" }},
            ]}}
          />
          {{mode === "solo" || mode === "uniqueMiss" ? (
            <Select
              value={{focusModel}}
              onChange={{(v) => {{
                setFocusModel(v);
                setPage(0);
                setSelected(null);
              }}}}
              options={{MODELS.map((m) => ({{
                value: m,
                label:
                  mode === "solo"
                    ? `${{m}} solo (${{DATA.c.solo[m] || 0}})`
                    : `${{m}} unique miss (${{DATA.c.uniqueMiss[m] || 0}})`,
              }}))}}
            />
          ) : null}}
          <Select
            value={{topic}}
            onChange={{(v) => {{
              setTopic(v);
              setPage(0);
            }}}}
            options={{topicOptions}}
          />
        </Row>
        <TextInput
          value={{query}}
          onChange={{(v) => {{
            setQuery(v);
            setPage(0);
          }}}}
          placeholder="Search question text…"
        />
      </Stack>

      <Grid columns={{2}} gap={{14}}>
        <Card>
          <CardHeader trailing={{<Text size="small" tone="secondary">{{filtered.length}} shown</Text>}}>
            Questions
          </CardHeader>
          <CardBody>
            <Stack gap={{8}}>
              {{pageRows.map((row) => {{
                const active = selected !== null && selected[0] === row[0];
                const nh = nHits(row[2]);
                return (
                  <button
                    key={{row[0]}}
                    type="button"
                    onClick={{() => setSelected(row)}}
                    style={{{{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: 10,
                      borderRadius: 8,
                      cursor: "pointer",
                      border: active
                        ? "1px solid currentColor"
                        : "1px solid transparent",
                      background: "transparent",
                      color: "inherit",
                      font: "inherit",
                    }}}}
                  >
                    <Stack gap={{4}}>
                      <Text size="small" weight="semibold">
                        {{row[0]}}
                      </Text>
                      <Row gap={{6}} wrap>
                        <Pill size="sm" active={{nh === 0}}>
                          {{nh}}/5 hit
                        </Pill>
                        {{row[1].split(",").map((t) => (
                          <Pill key={{t}} size="sm">
                            {{t}}
                          </Pill>
                        ))}}
                      </Row>
                    </Stack>
                  </button>
                );
              }})}}
              {{pageRows.length === 0 ? (
                <Text tone="secondary">No questions match these filters.</Text>
              ) : null}}
              <Row gap={{8}} align="center">
                <Pill
                  size="sm"
                  active={{pageSafe > 0}}
                  onClick={{() => pageSafe > 0 && setPage(pageSafe - 1)}}
                >
                  Prev
                </Pill>
                <Text size="small" tone="secondary">
                  Page {{pageSafe + 1}} / {{pageCount}}
                </Text>
                <Pill
                  size="sm"
                  active={{pageSafe < pageCount - 1}}
                  onClick={{() =>
                    pageSafe < pageCount - 1 && setPage(pageSafe + 1)
                  }}
                >
                  Next
                </Pill>
              </Row>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Selected question</CardHeader>
          <CardBody>
            {{!selected ? (
              <Text tone="secondary">
                Click a question to see each model&apos;s answer.
              </Text>
            ) : (
              <Stack gap={{12}}>
                <Text weight="semibold">{{selected[0]}}</Text>
                <Row gap={{6}} wrap>
                  {{selected[1].split(",").map((t) => (
                    <Pill key={{t}} size="sm" active>
                      {{t}}
                    </Pill>
                  ))}}
                </Row>
                <Text size="small" tone="secondary">
                  Hits: {{hitsFromMask(selected[2]).join(", ") || "none"}} ·
                  Misses: {{missesFromMask(selected[2]).join(", ") || "none"}}
                </Text>
                <Text weight="semibold" size="small">
                  Survey board (correct answers)
                </Text>
                <Table
                  headers={{["#", "Answer", "Pts"]}}
                  columnAlign={{["right", "left", "right"]}}
                  rows={{(selected[5] || []).map((pair, idx) => [
                    String(idx + 1),
                    pair[0],
                    String(pair[1]),
                  ])}}
                />
                <Text weight="semibold" size="small">
                  Model answers
                </Text>
                <Table
                  headers={{["Model", "Result", "Answer", "Matched board", "Pts"]}}
                  columnAlign={{["left", "left", "left", "left", "right"]}}
                  rows={{MODELS.map((name, i) => {{
                    const hit = (selected[2] & (1 << i)) !== 0;
                    return [
                      name,
                      hit ? "HIT" : "MISS",
                      selected[3][i] || "—",
                      (selected[6] && selected[6][i]) || "—",
                      String(selected[4][i]),
                    ];
                  }})}}
                  rowTone={{MODELS.map((_, i) =>
                    (selected[2] & (1 << i)) !== 0 ? "success" : "danger"
                  )}}
                />
              </Stack>
            )}}
          </CardBody>
        </Card>
      </Grid>

      <Divider />
      <Stack gap={{8}}>
        <H2>Solo hits vs unique misses (full set)</H2>
        <Table
          headers={{["Model", "Solo hits", "Unique misses"]}}
          columnAlign={{["left", "right", "right"]}}
          rows={{MODELS.map((m) => [
            m,
            String(DATA.c.solo[m] || 0),
            String(DATA.c.uniqueMiss[m] || 0),
          ])}}
        />
      </Stack>
      <Spacer />
      <Text tone="secondary" size="small">
        Example: open All models wrong, filter topic dating/sex, click a row —
        every model answer shows as MISS. Source: multi_provider_all_questions.json
        · Google Flash omitted (incomplete run).
      </Text>
    </Stack>
  );
}}
'''


def main() -> None:
    print("Scoring & building explorer…")
    data = build_rows()
    OUT_JSON.write_text(json.dumps(data), encoding="utf-8")
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace(
        "__N__", f"{data['n']:,}"
    )
    OUT_HTML.write_text(html, encoding="utf-8")
    ARTIFACT_HTML.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_HTML.write_text(html, encoding="utf-8")
    src = canvas_source(data)
    OUT_CANVAS_SRC.write_text(src, encoding="utf-8")
    print(
        f"Wrote {OUT_HTML} ({OUT_HTML.stat().st_size:,} bytes), "
        f"miss={data['c']['miss']}, disagree={data['c']['disagree']}, "
        f"uniqueMiss={data['c']['uniqueMiss']}"
    )


if __name__ == "__main__":
    main()
