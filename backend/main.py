import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from backend.config import GENERATED_APPS_DIR, LOGS_DIR
from backend.schemas import (
    PipelineStatusResponse, StartupIdeaPackage, TraceEvent
)
from backend.scheduler import pipeline_scheduler

app = FastAPI(
    title="Autonomous Idea & Prototype Generator Agent System",
    description="Multi-agent hourly pipeline built with Google ADK in Python",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    pipeline_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    pipeline_scheduler.stop()

# ----------------- PIPELINE CONTROL ENDPOINTS -----------------

@app.get("/api/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    return PipelineStatusResponse(
        is_pipeline_active=pipeline_scheduler.is_pipeline_active,
        execution_count=pipeline_scheduler.execution_count,
        last_run_timestamp=pipeline_scheduler.last_run_timestamp,
        current_run_project_id=pipeline_scheduler.current_run_project_id,
        next_scheduled_run="Top of next hour (00m)"
    )

@app.post("/api/pipeline/start")
async def start_pipeline():
    pipeline_scheduler.is_pipeline_active = True
    return {"message": "Pipeline scheduler enabled (Active)"}

@app.post("/api/pipeline/stop")
async def stop_pipeline():
    pipeline_scheduler.is_pipeline_active = False
    return {"message": "Pipeline scheduler paused"}

@app.post("/api/pipeline/run-now")
async def run_pipeline_now():
    asyncio.create_task(pipeline_scheduler.trigger_pipeline(is_manual=True))
    return {"message": "Pipeline run triggered asynchronously"}

# ----------------- HITL & MEMORY ENDPOINTS -----------------

@app.get("/api/hitl/pending")
async def get_pending_hitl():
    from backend.hitl import hitl_manager
    return hitl_manager.pending_approvals

@app.post("/api/hitl/approve/{approval_id}")
async def approve_hitl(approval_id: str):
    from backend.hitl import hitl_manager
    success = hitl_manager.approve_step(approval_id)
    if not success:
        raise HTTPException(status_code=404, detail="Approval ID not found")
    return {"status": "success", "message": f"Approved step {approval_id}"}

@app.get("/api/memory/{project_id}")
async def get_session_memory(project_id: str):
    from backend.memory import session_store
    session = session_store.load_session(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session memory not found")
    return session


# ----------------- STARTUP IDEAS & FILE ENDPOINTS -----------------

@app.get("/api/ideas", response_model=List[StartupIdeaPackage])
async def list_ideas():
    ideas = []
    if not GENERATED_APPS_DIR.exists():
        return ideas

    for project_dir in GENERATED_APPS_DIR.iterdir():
        if project_dir.is_dir():
            meta_file = project_dir / "package_metadata.json"
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    ideas.append(data)
                except Exception as e:
                    print(f"Error reading metadata for {project_dir.name}: {e}")
                    
    # Sort newest first
    ideas.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return ideas

@app.get("/api/ideas/{project_id}", response_model=StartupIdeaPackage)
async def get_idea(project_id: str):
    meta_file = GENERATED_APPS_DIR / project_id / "package_metadata.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Startup idea not found")
    data = json.loads(meta_file.read_text(encoding="utf-8"))
    return data

@app.get("/api/ideas/{project_id}/files")
async def get_idea_file_tree(project_id: str):
    project_dir = GENERATED_APPS_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    file_tree = []
    for root, dirs, files in os.walk(project_dir):
        for f in files:
            full = Path(root) / f
            rel = str(full.relative_to(project_dir))
            file_tree.append({
                "path": rel,
                "size": full.stat().st_size,
                "name": f
            })
    return file_tree

@app.get("/api/ideas/{project_id}/file-content")
async def get_idea_file_content(project_id: str, relative_path: str = Query(...)):
    project_dir = (GENERATED_APPS_DIR / project_id).resolve()
    file_path = (project_dir / relative_path).resolve()
    
    if not str(file_path).startswith(str(project_dir)) or not file_path.exists():
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    return {"path": relative_path, "content": file_path.read_text(encoding="utf-8")}

@app.get("/api/traces", response_model=List[TraceEvent])
async def get_traces():
    traces = []
    log_file = LOGS_DIR / "pipeline_traces.jsonl"
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        traces.append(json.loads(line))
                    except Exception:
                        pass
    return traces

# ----------------- WEBSOCKET REAL-TIME TRACE STREAMING -----------------

@app.websocket("/ws/trace")
async def websocket_trace_endpoint(websocket: WebSocket):
    await websocket.accept()
    pipeline_scheduler.add_listener(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pipeline_scheduler.remove_listener(websocket)
    except Exception:
        pipeline_scheduler.remove_listener(websocket)

# ----------------- STATIC PREVIEW SERVING -----------------

@app.get("/preview/{project_id}/{file_path:path}")
async def serve_preview_file(project_id: str, file_path: str):
    project_dir = (GENERATED_APPS_DIR / project_id).resolve()
    if not file_path or file_path == "":
        file_path = "index.html"
    target_path = (project_dir / file_path).resolve()
    if not str(target_path).startswith(str(project_dir)) or not target_path.exists():
        target_path = project_dir / "index.html"
    return FileResponse(target_path)

@app.get("/preview/{project_id}")
async def serve_preview_root(project_id: str):
    return await serve_preview_file(project_id, "index.html")

# ----------------- FRONTEND DASHBOARD HTML -----------------

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>5-Day Agent - Autonomous Idea & Prototype Generator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #07090e;
      --bg-panel: rgba(15, 23, 42, 0.8);
      --bg-card: rgba(30, 41, 59, 0.5);
      --border-panel: rgba(255, 255, 255, 0.08);
      --accent-blue: #3b82f6;
      --accent-purple: #8b5cf6;
      --accent-emerald: #10b981;
      --text-main: #f8fafc;
      --text-sub: #94a3b8;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: 'Inter', sans-serif;
      min-height: 100vh;
      overflow-x: hidden;
    }

    /* Layout */
    .app-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.25rem 2rem;
      background: var(--bg-panel);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-panel);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-logo {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.2rem;
    }

    .brand-title {
      font-size: 1.25rem;
      font-weight: 700;
      background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .controls-group {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--accent-emerald);
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 600;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      background-color: var(--accent-emerald);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--accent-emerald);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0% { opacity: 0.4; }
      50% { opacity: 1; }
      100% { opacity: 0.4; }
    }

    .btn {
      padding: 0.6rem 1.25rem;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      font-size: 0.9rem;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
      color: #fff;
    }
    .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(59,130,246,0.4); }

    .btn-outline {
      background: transparent;
      border: 1px solid var(--border-panel);
      color: var(--text-main);
    }
    .btn-outline:hover { background: rgba(255,255,255,0.05); }

    /* Main Container */
    .dashboard-container {
      display: grid;
      grid-template-columns: 1fr 380px;
      gap: 2rem;
      max-width: 1600px;
      margin: 2rem auto;
      padding: 0 2rem;
    }

    /* Startup Card Grid */
    .feed-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .feed-title {
      font-size: 1.5rem;
      font-weight: 700;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 1.5rem;
    }

    .startup-card {
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      border-radius: 16px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: all 0.3s;
      position: relative;
    }
    .startup-card:hover {
      transform: translateY(-4px);
      border-color: rgba(59, 130, 246, 0.4);
      box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    }

    .card-tags {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-bottom: 1rem;
    }

    .tag-industry {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .tag-score {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .card-title {
      font-size: 1.3rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      color: #fff;
    }

    .card-tagline {
      color: var(--text-sub);
      font-size: 0.9rem;
      margin-bottom: 1rem;
      line-height: 1.4;
    }

    .card-metrics {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      background: rgba(0,0,0,0.2);
      padding: 0.75rem;
      border-radius: 8px;
      margin-bottom: 1.25rem;
    }

    .metric-label { font-size: 0.75rem; color: var(--text-sub); }
    .metric-val { font-size: 0.95rem; font-weight: 600; color: #f1f5f9; }

    .card-actions {
      display: flex;
      gap: 0.75rem;
    }

    /* Trace Sidebar Drawer */
    .trace-drawer {
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      border-radius: 16px;
      padding: 1.5rem;
      height: calc(100vh - 120px);
      position: sticky;
      top: 100px;
      display: flex;
      flex-direction: column;
    }

    .trace-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border-panel);
      margin-bottom: 1rem;
    }

    .trace-log {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
    }

    .trace-item {
      padding: 0.75rem;
      border-radius: 8px;
      background: rgba(0,0,0,0.3);
      border-left: 3px solid var(--accent-blue);
    }
    .trace-item.THOUGHT { border-left-color: var(--accent-purple); }
    .trace-item.TOOL_EXECUTION { border-left-color: var(--accent-emerald); }
    .trace-item.STATUS_CHANGE { border-left-color: #f59e0b; }

    .trace-meta {
      display: flex;
      justify-content: space-between;
      color: var(--text-sub);
      font-size: 0.7rem;
      margin-bottom: 0.25rem;
    }

    .trace-agent { font-weight: 600; color: #60a5fa; }

    /* Modal / Preview Overlay */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.85);
      backdrop-filter: blur(12px);
      z-index: 1000;
      display: none;
      justify-content: center;
      align-items: center;
      padding: 2rem;
    }

    .modal-content {
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      border-radius: 20px;
      width: 100%;
      max-width: 1300px;
      height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .modal-header {
      padding: 1.25rem 2rem;
      border-bottom: 1px solid var(--border-panel);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-tabs {
      display: flex;
      gap: 1rem;
    }

    .tab-btn {
      padding: 0.5rem 1.25rem;
      border-radius: 8px;
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-sub);
      cursor: pointer;
      font-weight: 600;
    }

    .tab-btn.active {
      background: rgba(59, 130, 246, 0.2);
      color: #60a5fa;
      border-color: rgba(59, 130, 246, 0.4);
    }

    .modal-body {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    .iframe-preview {
      width: 100%;
      height: 100%;
      border: none;
      background: #000;
    }

    .code-viewer {
      display: grid;
      grid-template-columns: 260px 1fr;
      width: 100%;
      height: 100%;
    }

    .file-tree {
      border-right: 1px solid var(--border-panel);
      padding: 1rem;
      overflow-y: auto;
      background: rgba(0,0,0,0.2);
    }

    .tree-item {
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-sub);
    }
    .tree-item:hover, .tree-item.active {
      background: rgba(59, 130, 246, 0.2);
      color: #fff;
    }

    .code-content {
      padding: 1.5rem;
      overflow: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      white-space: pre-wrap;
      color: #e2e8f0;
      background: #090d16;
    }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header class="app-header">
    <div class="brand">
      <div class="brand-logo">5D</div>
      <div>
        <div class="brand-title">5-Day Agent Dashboard</div>
        <div style="font-size: 0.75rem; color: var(--text-sub);">Google ADK Autonomous Prototype Engine</div>
      </div>
    </div>

    <div class="controls-group">
      <div class="status-badge" id="status-badge">
        <div class="status-dot"></div>
        <span id="status-text">Pipeline Active (Hourly)</span>
      </div>

      <button class="btn btn-outline" id="toggle-scheduler-btn" onclick="toggleScheduler()">Pause Hourly Cron</button>
      <button class="btn btn-primary" onclick="triggerRunNow()">🚀 Run Pipeline Now</button>
    </div>
  </header>

  <!-- Main Workspace Layout -->
  <div class="dashboard-container">
    
    <!-- Left: Generated Startup Card Feed -->
    <main>
      <div class="feed-header">
        <div>
          <div class="feed-title">Generated Startup Packages</div>
          <div style="font-size: 0.85rem; color: var(--text-sub);">Real-time product concepts & React prototypes</div>
        </div>
        <button class="btn btn-outline" onclick="loadIdeas()">Refresh Feed</button>
      </div>

      <div class="cards-grid" id="cards-grid">
        <!-- Rendered via JS -->
      </div>
    </main>

    <!-- Right: Real-time Telemetry & Agent Trace Drawer -->
    <aside class="trace-drawer">
      <div class="trace-header">
        <div>
          <div style="font-weight: 700; font-size: 1rem;">Live Agent Trace Stream</div>
          <div style="font-size: 0.75rem; color: var(--text-sub);">WebSocket ADK Telemetry</div>
        </div>
        <span class="tag-score" style="font-size: 0.7rem;" id="ws-status">Connected</span>
      </div>

      <div class="trace-log" id="trace-log">
        <div class="trace-item STATUS_CHANGE">
          <div class="trace-meta">
            <span class="trace-agent">System</span>
            <span>Now</span>
          </div>
          <div>Listening for ADK agent pipeline execution traces...</div>
        </div>
      </div>
    </aside>

  </div>

  <!-- Interactive Modal for Live Preview & Code Viewer -->
  <div class="modal-overlay" id="preview-modal">
    <div class="modal-content">
      <div class="modal-header">
        <div>
          <h2 id="modal-app-name" style="font-size: 1.25rem;">App Prototype</h2>
          <div id="modal-project-id" style="font-size: 0.8rem; color: var(--text-sub);">project_id</div>
        </div>

        <div class="modal-tabs">
          <button class="tab-btn active" id="tab-live-btn" onclick="switchModalTab('live')">🌐 Live Interactive Preview</button>
          <button class="tab-btn" id="tab-code-btn" onclick="switchModalTab('code')">💻 Source Code Inspector</button>
        </div>

        <button class="btn btn-outline" onclick="closeModal()">✕ Close</button>
      </div>

      <div class="modal-body">
        <!-- Tab 1: Live Iframe Preview -->
        <iframe class="iframe-preview" id="modal-iframe" src="about:blank"></iframe>

        <!-- Tab 2: Code Viewer -->
        <div class="code-viewer" id="modal-code-container" style="display: none;">
          <div class="file-tree" id="modal-file-tree">
            <!-- Files rendered here -->
          </div>
          <pre class="code-content" id="modal-code-display">// Select a file to view source code</pre>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentIdeas = [];
    let currentProjectId = null;
    let ws = null;
    let schedulerActive = true;

    async function init() {
      await checkStatus();
      await loadIdeas();
      await loadTracesHistory();
      connectWebSocket();
    }

    async function checkStatus() {
      try {
        const res = await fetch('/api/pipeline/status');
        const data = await res.json();
        schedulerActive = data.is_pipeline_active;
        updateSchedulerUI();
      } catch (e) {
        console.error(e);
      }
    }

    function updateSchedulerUI() {
      const badgeText = document.getElementById('status-text');
      const toggleBtn = document.getElementById('toggle-scheduler-btn');
      if (schedulerActive) {
        badgeText.textContent = "Pipeline Active (Hourly)";
        toggleBtn.textContent = "Pause Hourly Cron";
      } else {
        badgeText.textContent = "Pipeline Paused";
        toggleBtn.textContent = "Enable Hourly Cron";
      }
    }

    async function toggleScheduler() {
      const endpoint = schedulerActive ? '/api/pipeline/stop' : '/api/pipeline/start';
      await fetch(endpoint, { method: 'POST' });
      schedulerActive = !schedulerActive;
      updateSchedulerUI();
    }

    async function triggerRunNow() {
      await fetch('/api/pipeline/run-now', { method: 'POST' });
      appendTraceItem({
        agent_name: 'System',
        event_type: 'STATUS_CHANGE',
        content: 'Manual pipeline run triggered by user.',
        timestamp: new Date().toISOString()
      });
    }

    async function loadIdeas() {
      try {
        const res = await fetch('/api/ideas');
        currentIdeas = await res.json();
        renderIdeas();
      } catch (e) {
        console.error(e);
      }
    }

    function renderIdeas() {
      const grid = document.getElementById('cards-grid');
      if (currentIdeas.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 4rem; text-align: center; background: var(--bg-panel); border-radius: 16px;">
            <h3>No Startup Packages Generated Yet</h3>
            <p style="color: var(--text-sub); margin-top: 0.5rem;">Click "Run Pipeline Now" to execute the 4-agent ADK discovery pipeline.</p>
          </div>
        `;
        return;
      }

      grid.innerHTML = currentIdeas.map(idea => `
        <div class="startup-card">
          <div>
            <div class="card-tags">
              <span class="tag-industry">${idea.discovery.target_industry}</span>
              <span class="tag-score">Score: ${idea.discovery.opportunity_score}/10</span>
            </div>
            <div class="card-title">${idea.product_spec.app_name}</div>
            <div class="card-tagline">${idea.product_spec.tagline}</div>

            <div class="card-metrics">
              <div>
                <div class="metric-label">TAM Size</div>
                <div class="metric-val">${idea.market_research.market_size_tam}</div>
              </div>
              <div>
                <div class="metric-label">Build Status</div>
                <div class="metric-val" style="color: #10b981;">${idea.build_artifact ? idea.build_artifact.build_status : 'PENDING'}</div>
              </div>
            </div>
          </div>

          <div class="card-actions">
            <button class="btn btn-primary" style="flex:1" onclick="openPreview('${idea.project_id}')">
              🌐 Live App
            </button>
            <button class="btn btn-outline" onclick="openCodeInspector('${idea.project_id}')">
              💻 Source
            </button>
          </div>
        </div>
      `).join('');
    }

    async function loadTracesHistory() {
      try {
        const res = await fetch('/api/traces');
        const traces = await res.json();
        traces.slice(-20).forEach(appendTraceItem);
      } catch (e) {
        console.error(e);
      }
    }

    function appendTraceItem(event) {
      const log = document.getElementById('trace-log');
      const item = document.createElement('div');
      item.className = `trace-item ${event.event_type}`;
      
      const timeStr = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';
      item.innerHTML = `
        <div class="trace-meta">
          <span class="trace-agent">${event.agent_name}</span>
          <span>${timeStr}</span>
        </div>
        <div>${event.content}</div>
      `;
      log.appendChild(item);
      log.scrollTop = log.scrollHeight;
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${protocol}//${window.location.host}/ws/trace`);

      ws.onopen = () => {
        document.getElementById('ws-status').textContent = 'Live Connected';
      };

      ws.onmessage = (event) => {
        try {
          const trace = JSON.parse(event.data);
          appendTraceItem(trace);
          if (trace.event_type === 'STATUS_CHANGE' && trace.content.includes('Pipeline finished')) {
            loadIdeas();
          }
        } catch (e) {
          console.error(e);
        }
      };

      ws.onclose = () => {
        document.getElementById('ws-status').textContent = 'Reconnecting...';
        setTimeout(connectWebSocket, 3000);
      };
    }

    /* Modal Handling */
    function openPreview(projectId) {
      const idea = currentIdeas.find(i => i.project_id === projectId);
      if (!idea) return;

      currentProjectId = projectId;
      document.getElementById('modal-app-name').textContent = idea.product_spec.app_name;
      document.getElementById('modal-project-id').textContent = `Project: ${projectId}`;
      document.getElementById('modal-iframe').src = `/preview/${projectId}/index.html`;

      switchModalTab('live');
      document.getElementById('preview-modal').style.display = 'flex';
    }

    async function openCodeInspector(projectId) {
      openPreview(projectId);
      switchModalTab('code');
    }

    function switchModalTab(tab) {
      const liveBtn = document.getElementById('tab-live-btn');
      const codeBtn = document.getElementById('tab-code-btn');
      const iframe = document.getElementById('modal-iframe');
      const codeContainer = document.getElementById('modal-code-container');

      if (tab === 'live') {
        liveBtn.classList.add('active');
        codeBtn.classList.remove('active');
        iframe.style.display = 'block';
        codeContainer.style.display = 'none';
      } else {
        codeBtn.classList.add('active');
        liveBtn.classList.remove('active');
        iframe.style.display = 'none';
        codeContainer.style.display = 'grid';
        loadProjectFileTree(currentProjectId);
      }
    }

    async function loadProjectFileTree(projectId) {
      try {
        const res = await fetch(`/api/ideas/${projectId}/files`);
        const files = await res.json();
        const treeBox = document.getElementById('modal-file-tree');
        treeBox.innerHTML = files.map(f => `
          <div class="tree-item" onclick="loadFileContent('${projectId}', '${f.path}', this)">
            📄 ${f.path}
          </div>
        `).join('');

        if (files.length > 0) {
          // Select App.jsx or first file
          const defaultFile = files.find(f => f.path.includes('App.jsx')) || files[0];
          loadFileContent(projectId, defaultFile.path);
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function loadFileContent(projectId, relPath, element) {
      if (element) {
        document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('active'));
        element.classList.add('active');
      }

      try {
        const res = await fetch(`/api/ideas/${projectId}/file-content?relative_path=${encodeURIComponent(relPath)}`);
        const data = await res.json();
        document.getElementById('modal-code-display').textContent = data.content;
      } catch (e) {
        console.error(e);
      }
    }

    function closeModal() {
      document.getElementById('preview-modal').style.display = 'none';
      document.getElementById('modal-iframe').src = 'about:blank';
    }

    window.onload = init;
  </script>
</body>
</html>
"""
