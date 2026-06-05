"""Agent-DAG-Monitor API für SPEC-0037.

FR-01: GET /api/orchestrate/runs — Run-Liste
FR-02: GET /api/orchestrate/stream/{run_id} — SSE DagEvent-Stream
FR-04: POST /api/orchestrate/command/{run_id} — SchedulerCommand

Nutzt SPEC-0007-Infrastruktur (DagEventBus auf SSE-Basis, SPEC-0016 Job-Push).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[4]))
from sdd_cli.dag_event import DagEvent, EscalationEvent, get_event_bus
from sdd_cli.dag_command import build_command, get_command_queue

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Run registry (in-memory, leichtgewichtig – kein Persistenz-Anspruch)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DagRunEntry:
    run_id: str
    spec_id: str
    status: str = "running"
    started_at: float = field(default_factory=time.time)

_runs: dict[str, DagRunEntry] = {}
_TTL = 3600.0


def register_run(run_id: str, spec_id: str) -> None:
    """Wird von sdd implement aufgerufen wenn ein Run startet."""
    _cleanup()
    _runs[run_id] = DagRunEntry(run_id=run_id, spec_id=spec_id)


def finish_run(run_id: str, status: str = "done") -> None:
    entry = _runs.get(run_id)
    if entry:
        entry.status = status


def _cleanup() -> None:
    now = time.time()
    stale = [k for k, v in _runs.items() if now - v.started_at > _TTL]
    for k in stale:
        _runs.pop(k, None)


def _runs_list(max_history: int = 5) -> list[dict]:
    _cleanup()
    entries = sorted(_runs.values(), key=lambda e: e.started_at, reverse=True)
    running = [e for e in entries if e.status == "running"]
    done = [e for e in entries if e.status != "running"][:max_history]
    return [
        {
            "run_id":     e.run_id,
            "spec_id":    e.spec_id,
            "status":     e.status,
            "started_at": e.started_at,
        }
        for e in running + done
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    command_type: str
    task_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/orchestrate", response_class=HTMLResponse, include_in_schema=False)
def orchestrate_ui() -> HTMLResponse:
    return HTMLResponse(_DAG_MONITOR_HTML)


@router.get("/orchestrate/runs", summary="Laufende + abgeschlossene DAG-Runs (SPEC-0037 FR-01)")
def list_runs() -> list[dict]:
    try:
        from sdd_context import get_config
        max_h = get_config().dag_monitor_max_runs_history()
    except Exception:
        max_h = 5
    return _runs_list(max_h)


@router.get(
    "/orchestrate/stream/{run_id}",
    summary="SSE DagEvent-Stream für einen Run (SPEC-0037 FR-02)",
)
async def stream_dag_events(run_id: str) -> StreamingResponse:
    bus = get_event_bus()

    try:
        from sdd_context import get_config
        heartbeat = get_config().dag_monitor_sse_heartbeat()
    except Exception:
        heartbeat = 15

    async def _generate():
        # SSE-Header-Kommentar als sofortiger Flush
        yield ": connected\n\n"
        last_event = time.monotonic()
        try:
            async for event in bus.subscribe(run_id):
                data = event.model_dump_json()
                yield f"data: {data}\n\n"
                last_event = time.monotonic()
        except asyncio.CancelledError:
            return
        finally:
            # Keep-Alive-Heartbeat-Aufgabe endet mit Generator
            pass

    async def _generate_with_heartbeat():
        gen = _generate()
        heartbeat_task: asyncio.Task | None = None

        async def send_heartbeats(q: asyncio.Queue):
            while True:
                await asyncio.sleep(heartbeat)
                await q.put(None)

        hb_queue: asyncio.Queue = asyncio.Queue()
        heartbeat_task = asyncio.create_task(send_heartbeats(hb_queue))

        try:
            async for chunk in gen:
                yield chunk
                # Drain heartbeat queue
                while not hb_queue.empty():
                    hb_queue.get_nowait()
                    yield ": heartbeat\n\n"
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()

    return StreamingResponse(
        _generate_with_heartbeat(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


@router.post(
    "/orchestrate/command/{run_id}",
    status_code=202,
    summary="SchedulerCommand an laufenden Run senden (SPEC-0037 FR-04)",
)
def send_command(run_id: str, body: CommandRequest) -> dict[str, Any]:
    try:
        cmd = build_command(run_id=run_id, task_id=body.task_id, command_type=body.command_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    q = get_command_queue()
    try:
        q.enqueue_sync(cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"queued": True, "run_id": run_id, "command_type": body.command_type, "task_id": body.task_id}


# ─────────────────────────────────────────────────────────────────────────────
# WebUI: /orchestrate  (FR-03, FR-05, FR-17)
# ─────────────────────────────────────────────────────────────────────────────

_DAG_MONITOR_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Agent DAG Monitor · SDD</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  :root{--bg:#0f1117;--surface:#1a1d26;--border:#2d3142;--text:#e2e8f0;--muted:#64748b;
        --blue:#3b82f6;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--gray:#6b7280}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;font-size:14px;min-height:100vh}
  header{background:var(--surface);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;align-items:center;gap:12px}
  header h1{font-size:16px;font-weight:600}header span{color:var(--muted);font-size:12px}
  .layout{display:grid;grid-template-columns:280px 1fr;height:calc(100vh - 49px)}
  .sidebar{background:var(--surface);border-right:1px solid var(--border);overflow-y:auto;padding:12px}
  .sidebar h2{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:8px}
  .run-item{padding:10px 12px;border-radius:6px;cursor:pointer;margin-bottom:4px;border:1px solid transparent;transition:all .15s}
  .run-item:hover{background:#1e2130;border-color:var(--border)}
  .run-item.active{background:#1e2130;border-color:var(--blue)}
  .run-item .spec{font-weight:500;font-size:13px}
  .run-item .meta{font-size:11px;color:var(--muted);margin-top:2px;display:flex;gap:8px;align-items:center}
  .badge{display:inline-block;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:600;text-transform:uppercase}
  .badge-running{background:#1d3557;color:var(--blue)}
  .badge-done{background:#14532d;color:var(--green)}
  .badge-failed{background:#450a0a;color:var(--red)}
  .main{padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:16px}
  .dag-container{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;min-height:200px}
  .dag-container h3{font-size:13px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px}
  #mermaid-output{overflow-x:auto}
  .node-table{width:100%;border-collapse:collapse}
  .node-table th{text-align:left;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;padding:6px 10px;border-bottom:1px solid var(--border)}
  .node-table td{padding:8px 10px;border-bottom:1px solid #1e2130;font-size:12px;vertical-align:middle}
  .node-table tr:last-child td{border-bottom:none}
  .status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
  .dot-pending{background:var(--gray)}.dot-running{background:var(--blue);animation:pulse 1s infinite}
  .dot-done{background:var(--green)}.dot-failed{background:var(--red)}
  .dot-paused{background:var(--yellow)}.dot-skipped{background:var(--gray);opacity:.4}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .cmd-btn{padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;cursor:pointer;border:1px solid var(--border);background:#1e2130;color:var(--text);transition:all .1s;margin-right:2px}
  .cmd-btn:hover{background:var(--border)}
  .cmd-btn.danger{border-color:#7f1d1d;color:var(--red)}.cmd-btn.success{border-color:#14532d;color:var(--green)}
  .kanban-link{font-size:11px;color:var(--blue);text-decoration:none;margin-left:auto}
  .kanban-link:hover{text-decoration:underline}
  .escalation-banner{background:#450a0a;border:1px solid #7f1d1d;border-radius:8px;padding:16px;display:none}
  .escalation-banner.visible{display:block}
  .escalation-banner h3{color:var(--red);font-size:14px;margin-bottom:6px}
  .escalation-banner p{color:#fca5a5;font-size:12px;margin-bottom:12px}
  .escalation-actions{display:flex;gap:8px}
  .esc-btn{padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;border:none}
  .esc-btn.retry{background:var(--blue);color:#fff}.esc-btn.skip{background:#374151;color:var(--text)}.esc-btn.abort{background:#7f1d1d;color:var(--red)}
  .empty-state{color:var(--muted);font-size:13px;text-align:center;padding:40px}
  #status-bar{font-size:11px;color:var(--muted);padding:4px 0}
</style>
</head>
<body>
<header>
  <h1>Agent DAG Monitor</h1>
  <span>SPEC-0037</span>
</header>
<div class="layout">
  <nav class="sidebar">
    <h2>Runs</h2>
    <div id="run-list"><div class="empty-state">Keine laufenden Runs.</div></div>
  </nav>
  <main class="main">
    <div id="escalation-banner" class="escalation-banner">
      <h3>⚠ Autopilot eskaliert</h3>
      <p id="escalation-reason"></p>
      <div class="escalation-actions">
        <button class="esc-btn retry" onclick="sendEscalation('retry')">Retry</button>
        <button class="esc-btn skip" onclick="sendEscalation('skip')">Skip Task</button>
        <button class="esc-btn abort" onclick="sendEscalation('abort')">Abort</button>
      </div>
    </div>
    <div class="dag-container">
      <h3 id="dag-title">
        <span>DAG</span>
        <a id="kanban-link" class="kanban-link" href="#" style="display:none">→ Kanban-Board</a>
      </h3>
      <div id="mermaid-output"><div class="empty-state">Run in der Sidebar auswählen.</div></div>
    </div>
    <div class="dag-container">
      <h3>Tasks</h3>
      <div id="status-bar"></div>
      <table class="node-table" id="task-table">
        <thead><tr>
          <th>Task</th><th>Status</th><th>Agent</th><th>Dauer</th><th>Aktionen</th>
        </tr></thead>
        <tbody id="task-tbody"></tbody>
      </table>
    </div>
  </main>
</div>

<script>
mermaid.initialize({startOnLoad:false,theme:'dark',securityLevel:'loose'});

const API = '/api';
let currentRunId = null;
let currentSpecId = null;
let sse = null;
const tasks = {}; // task_id → {task_id, status, agent, model, start_ms, title}
const escapedEscalation = {run_id: null, task_id: null};

async function loadRuns() {
  try {
    const r = await fetch(`${API}/orchestrate/runs`);
    const runs = await r.json();
    const el = document.getElementById('run-list');
    if (!runs.length) { el.innerHTML = '<div class="empty-state">Keine Runs.</div>'; return; }
    el.innerHTML = runs.map(run => `
      <div class="run-item${run.run_id===currentRunId?' active':''}" onclick="selectRun('${run.run_id}','${run.spec_id}')">
        <div class="spec">${run.spec_id}</div>
        <div class="meta">
          <span class="badge badge-${run.status}">${run.status}</span>
          <span>${new Date(run.started_at*1000).toLocaleTimeString('de')}</span>
        </div>
      </div>`).join('');
  } catch(e) { console.error(e); }
}

function selectRun(runId, specId) {
  if (currentRunId === runId) return;
  currentRunId = runId;
  currentSpecId = specId;
  Object.keys(tasks).forEach(k => delete tasks[k]);
  document.getElementById('task-tbody').innerHTML = '';
  document.getElementById('mermaid-output').innerHTML = '<div class="empty-state">Warte auf Events…</div>';
  document.getElementById('escalation-banner').classList.remove('visible');
  const kl = document.getElementById('kanban-link');
  kl.href = `/specs/${specId}/tasks`; kl.style.display='inline';
  document.getElementById('dag-title').querySelector('span').textContent = `DAG · ${specId}`;
  document.getElementById('status-bar').textContent = `Run: ${runId}`;
  if (sse) { sse.close(); sse = null; }
  connectSSE(runId);
  loadRuns();
}

function connectSSE(runId) {
  sse = new EventSource(`${API}/orchestrate/stream/${runId}`);
  sse.onmessage = e => {
    try { handleEvent(JSON.parse(e.data)); } catch(err) { console.warn(err, e.data); }
  };
  sse.onerror = () => { setTimeout(() => { if(currentRunId===runId) connectSSE(runId); }, 3000); };
}

function handleEvent(ev) {
  if (!tasks[ev.task_id]) {
    tasks[ev.task_id] = {task_id: ev.task_id, status:'pending', agent:'none', model:'', start_ms:null, title: ev.task_id};
  }
  const t = tasks[ev.task_id];
  t.status = ev.status;
  t.agent = ev.agent || 'none';
  t.model = ev.model || '';
  if (ev.status === 'running' && !t.start_ms) t.start_ms = Date.now();
  if (ev.status === 'done' || ev.status === 'failed') t.end_ms = Date.now();
  if (ev.details) t.title = ev.details || ev.task_id;

  // Handle escalation
  if (ev.status === 'failed' && ev.phase) {
    showEscalation(ev);
  }

  renderTable();
  renderMermaid();
}

function showEscalation(ev) {
  escapedEscalation.run_id = ev.run_id;
  escapedEscalation.task_id = ev.task_id;
  document.getElementById('escalation-reason').textContent = ev.reason || ev.details || 'Unbekannter Fehler';
  document.getElementById('escalation-banner').classList.add('visible');
}

function sendEscalation(action) {
  if (!escapedEscalation.run_id || !escapedEscalation.task_id) return;
  sendCommand(escapedEscalation.run_id, escapedEscalation.task_id, action === 'retry' ? 'restart_task' : action === 'skip' ? 'skip_task' : 'skip_task');
  document.getElementById('escalation-banner').classList.remove('visible');
}

function renderTable() {
  const tbody = document.getElementById('task-tbody');
  const rows = Object.values(tasks);
  tbody.innerHTML = rows.map(t => {
    const dur = t.start_ms ? Math.round(((t.end_ms || Date.now()) - t.start_ms)/1000) + 's' : '—';
    const agentBadge = t.agent !== 'none'
      ? `<span style="font-size:10px;color:${t.agent==='local'?'#60a5fa':'#a78bfa'}">${t.agent.toUpperCase()}${t.model?': '+t.model:''}</span>`
      : '—';
    const statusHtml = `<span class="status-dot dot-${t.status}"></span>${t.status}`;
    const actions = buildActions(t);
    return `<tr><td title="${t.task_id}">${t.title.substring(0,40)}</td><td>${statusHtml}</td><td>${agentBadge}</td><td>${dur}</td><td>${actions}</td></tr>`;
  }).join('');
}

function buildActions(t) {
  const btns = [];
  if (t.status === 'running') btns.push(`<button class="cmd-btn" onclick="sendCommand('${currentRunId}','${t.task_id}','pause_task')">Pause</button>`);
  if (t.status === 'paused')  btns.push(`<button class="cmd-btn success" onclick="sendCommand('${currentRunId}','${t.task_id}','resume_task')">Resume</button>`);
  if (t.status === 'failed')  btns.push(`<button class="cmd-btn success" onclick="sendCommand('${currentRunId}','${t.task_id}','restart_task')">Restart</button>`);
  if (['pending','paused'].includes(t.status)) {
    btns.push(`<button class="cmd-btn" onclick="sendCommand('${currentRunId}','${t.task_id}','force_local')">↓ Local</button>`);
    btns.push(`<button class="cmd-btn" onclick="sendCommand('${currentRunId}','${t.task_id}','force_cloud')">↑ Cloud</button>`);
    btns.push(`<button class="cmd-btn danger" onclick="sendCommand('${currentRunId}','${t.task_id}','skip_task')">Skip</button>`);
  }
  return btns.join('') || '—';
}

async function sendCommand(runId, taskId, commandType) {
  try {
    const r = await fetch(`${API}/orchestrate/command/${runId}`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({command_type: commandType, task_id: taskId})
    });
    if (!r.ok) { const d = await r.json(); alert('Fehler: ' + (d.detail || r.status)); }
  } catch(e) { console.error(e); }
}

async function renderMermaid() {
  const nodes = Object.values(tasks);
  if (!nodes.length) return;
  const colorMap = {pending:'#374151',running:'#1d3557',done:'#14532d',failed:'#450a0a',paused:'#422006',skipped:'#1a1d26'};
  const textColorMap = {pending:'#9ca3af',running:'#60a5fa',done:'#4ade80',failed:'#f87171',paused:'#fde047',skipped:'#6b7280'};
  let graph = 'graph LR\n';
  nodes.forEach(t => {
    const lbl = `${t.task_id.substring(0,8)}<br/>${t.title.substring(0,20)}${t.model?'<br/>'+t.agent.toUpperCase()+': '+t.model.substring(0,15):''}`;
    graph += `  ${t.task_id}["${lbl}"]\n`;
    graph += `  style ${t.task_id} fill:${colorMap[t.status]||'#374151'},color:${textColorMap[t.status]||'#9ca3af'},stroke:#2d3142\n`;
  });
  const el = document.getElementById('mermaid-output');
  try {
    const {svg} = await mermaid.render('dag-' + Date.now(), graph);
    el.innerHTML = svg;
  } catch(e) { /* ignore render errors on intermediate states */ }
}

// Init
loadRuns();
setInterval(loadRuns, 10000);
</script>
</body>
</html>"""
