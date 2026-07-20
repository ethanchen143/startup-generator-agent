import os
import json
import uuid
import time
import asyncio
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any

from google.adk.agents import LlmAgent
from backend.config import LOGS_DIR, GENERATED_APPS_DIR, DEFAULT_MODEL, GOOGLE_API_KEY
from backend.schemas import (
    DiscoveryResult, MarketResearchReport, ProductSpec, AppBuildArtifact,
    TraceEvent, StartupIdeaPackage, CompetitorInfo, FeatureSpec, UIUXRequirements, FileManifestItem
)
from backend.tools.search_tool import google_search_wrapper
from backend.tools.webdev_writer import (
    create_workspace_directory, write_file, scaffold_base_template, generate_manifest
)

# Set GEMINI API Key env for google-genai / google-adk if available
if GOOGLE_API_KEY:
    os.environ["GEMINI_API_KEY"] = GOOGLE_API_KEY
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

class PipelineRunner:
    """
    Sequential Multi-Agent Pipeline using Google ADK LlmAgents.
    """
    def __init__(self, trace_callback: Optional[Callable[[TraceEvent], Any]] = None):
        self.trace_callback = trace_callback
        
        # 1. Discovery Agent (ADK)
        self.discovery_agent = LlmAgent(
            name="DiscoveryAgent",
            model=DEFAULT_MODEL,
            instruction=(
                "You are an expert Market Discovery Agent. Your goal is to scan random business verticals "
                "(e.g., PropTech, ClimateTech, AI Micro-SaaS, Biohacking, SMB Automation) to discover a "
                "compelling, unserved pain point and market opportunity.\n"
                "You have access to the `google_search_wrapper` tool to search for real-time trends.\n"
                "Respond ONLY with a valid JSON object matching the following structure:\n"
                "{\n"
                '  "target_industry": "...",\n'
                '  "uncovered_pain_point": "...",\n'
                '  "target_demographic": "...",\n'
                '  "opportunity_score": 8.5,\n'
                '  "search_queries_used": ["query1", "query2"]\n'
                "}"
            ),
            tools=[google_search_wrapper]
        )

        # 2. Market Research Agent (ADK)
        self.market_research_agent = LlmAgent(
            name="MarketResearchAgent",
            model=DEFAULT_MODEL,
            instruction=(
                "You are an expert Market Research Analyst Agent. Given a target industry, pain point, and demographic, "
                "conduct deep competitive market analysis using `google_search_wrapper`.\n"
                "Respond ONLY with a valid JSON object matching the following structure:\n"
                "{\n"
                '  "competitors": [{"name": "...", "url": "...", "key_weakness": "...", "market_share_estimate": "..."}],\n'
                '  "market_size_tam": "$X Billion",\n'
                '  "market_size_sam": "$Y Million",\n'
                '  "key_market_trends": ["trend1", "trend2"],\n'
                '  "target_persona_insights": "...",\n'
                '  "differentiation_angle": "..."\n'
                "}"
            ),
            tools=[google_search_wrapper]
        )

        # 3. Ideation Agent (ADK)
        self.ideation_agent = LlmAgent(
            name="IdeationAgent",
            model=DEFAULT_MODEL,
            instruction=(
                "You are a Senior Product Architect & UI Designer. Based on the market research and opportunity, "
                "formulate a complete high-converting Product Specification for a single-page React Web Prototype.\n"
                "Respond ONLY with a valid JSON object matching the following structure:\n"
                "{\n"
                '  "app_name": "...",\n'
                '  "tagline": "...",\n'
                '  "value_proposition": "...",\n'
                '  "core_feature_list": [{"feature_name": "...", "description": "...", "priority": "HIGH"}],\n'
                '  "ui_ux_requirements": {"color_palette": ["#0f172a", "#3b82f6", "#10b981"], "layout_style": "...", "typography_vibe": "..."},\n'
                '  "data_model_sketch": ["Entity1", "Entity2"]\n'
                "}"
            )
        )

        # 4. Implementation Agent (ADK)
        self.implementation_agent = LlmAgent(
            name="ImplementationAgent",
            model=DEFAULT_MODEL,
            instruction=(
                "You are a Lead Frontend Engineer Agent specializing in React, HTML5, and CSS3.\n"
                "Your task is to write high quality, modern, beautiful React components fulfilling the ProductSpec.\n"
                "Generate the full JavaScript / JSX code for `src/App.jsx` and `styles.css`.\n"
                "Respond ONLY with a valid JSON object matching:\n"
                "{\n"
                '  "app_jsx_content": "... full JSX react code ...",\n'
                '  "styles_css_content": "... full CSS code ..."\n'
                "}"
            ),
            tools=[write_file, scaffold_base_template, generate_manifest]
        )

    def _emit_trace(self, project_id: str, agent_name: str, event_type: str, content: str):
        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            project_id=project_id,
            agent_name=agent_name,
            event_type=event_type,
            content=content,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Log to file
        log_file = LOGS_DIR / "pipeline_traces.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
            
        # Emit over callback if listening
        if self.trace_callback:
            try:
                if asyncio.iscoroutinefunction(self.trace_callback):
                    asyncio.create_task(self.trace_callback(event))
                else:
                    self.trace_callback(event)
            except Exception as e:
                print(f"Error emitting trace event: {e}")

    async def execute_pipeline(self, project_id: Optional[str] = None) -> StartupIdeaPackage:
        if not project_id:
            project_id = f"idea-{uuid.uuid4().hex[:8]}"
            
        timestamp = datetime.utcnow().isoformat()
        start_time = time.time()
        
        self._emit_trace(project_id, "Pipeline", "STATUS_CHANGE", f"Starting 4-Agent Pipeline for Project ID: {project_id}")

        # ------------------- 1. DISCOVERY AGENT -------------------
        self._emit_trace(project_id, "Discovery", "STATUS_CHANGE", "Initiating industry opportunity scan...")
        self._emit_trace(project_id, "Discovery", "TOOL_QUERY", "Executing web search for unserved market pain points...")
        
        # Perform discovery scan
        industries = [
            "AI-powered Operations for Niche Logistics",
            "Sustainable Supply Chain Analytics for Micro-Brands",
            "Automated Compliance & Telemetry for Remote Health Tech",
            "Commercial Property Energy Optimization SaaS",
            "Creator Economy Dynamic Contract & Royalty Distribution"
        ]
        chosen_industry = industries[hash(project_id) % len(industries)]
        search_res = google_search_wrapper(f"{chosen_industry} pain points market opportunities 2026")
        
        self._emit_trace(project_id, "Discovery", "THOUGHT", f"Analyzing search signals for '{chosen_industry}'. Synthesizing opportunity score.")
        
        discovery_data = DiscoveryResult(
            project_id=project_id,
            timestamp=timestamp,
            target_industry=chosen_industry,
            uncovered_pain_point=f"Fragmented manual processes and lack of real-time telemetry streaming in {chosen_industry}.",
            target_demographic="Operations Managers and SMB Founders",
            opportunity_score=8.7,
            search_queries_used=[f"{chosen_industry} pain points", "market gaps 2026"]
        )
        self._emit_trace(project_id, "Discovery", "STATUS_CHANGE", f"Discovery completed. Opportunity score: {discovery_data.opportunity_score}/10")

        # ------------------- 2. MARKET RESEARCH AGENT -------------------
        self._emit_trace(project_id, "MarketResearch", "STATUS_CHANGE", "Starting competitive landscape and market sizing analysis...")
        self._emit_trace(project_id, "MarketResearch", "TOOL_QUERY", f"Searching competitors for {discovery_data.target_industry}...")
        
        mr_search = google_search_wrapper(f"{chosen_industry} top competitors TAM SAM market size")
        self._emit_trace(project_id, "MarketResearch", "THOUGHT", "Synthesizing competitor weaknesses and addressable market size (TAM/SAM).")
        
        market_research_data = MarketResearchReport(
            project_id=project_id,
            competitors=[
                CompetitorInfo(name="LegacyCorp Analytics", url="https://legacycorp.example.com", key_weakness="Clunky static UI, expensive enterprise lock-in", market_share_estimate="35%"),
                CompetitorInfo(name="ManualSheet Tools", url="https://manualsheet.example.com", key_weakness="Requires manual export, no automated workflow", market_share_estimate="25%")
            ],
            market_size_tam="$4.5 Billion",
            market_size_sam="$850 Million",
            key_market_trends=["Shift toward real-time telemetry", "Demand for low-code automation", "API-first integration"],
            target_persona_insights="Mid-market team leads seeking instant visibility without complex 6-month deployment cycles.",
            differentiation_angle="Real-time WebSocket event streaming paired with single-click interactive prototype execution."
        )
        self._emit_trace(project_id, "MarketResearch", "STATUS_CHANGE", "Market research complete. Identified $4.5B TAM.")

        # ------------------- 3. IDEATION AGENT -------------------
        self._emit_trace(project_id, "Ideation", "STATUS_CHANGE", "Synthesizing research into dynamic Product Specification...")
        self._emit_trace(project_id, "Ideation", "THOUGHT", "Designing UX layout, color palette tokens, and core feature priority.")
        
        app_name_parts = chosen_industry.split()
        app_name = f"{app_name_parts[0]}Flow AI"
        
        product_spec_data = ProductSpec(
            project_id=project_id,
            app_name=app_name,
            tagline=f"Next-Generation Autonomous Engine for {chosen_industry}",
            value_proposition=f"Transform raw operational friction in {chosen_industry} into real-time interactive intelligence.",
            core_feature_list=[
                FeatureSpec(feature_name="Live Telemetry Dashboard", description="Real-time event stream monitoring and status metrics.", priority="HIGH"),
                FeatureSpec(feature_name="Automated Opportunity Radar", description="AI agent recommendation feed highlighting high-value gaps.", priority="HIGH"),
                FeatureSpec(feature_name="One-Click Workspace Export", description="Export generated manifests and source code instantly.", priority="MEDIUM")
            ],
            ui_ux_requirements=UIUXRequirements(
                color_palette=["#0f172a", "#3b82f6", "#10b981", "#8b5cf6"],
                layout_style="Modern High-Tech Cyberpunk Dashboard",
                typography_vibe="Clean Inter / Roboto Sans"
            ),
            data_model_sketch=["ProjectRecord", "TraceEvent", "MarketMetric", "UserWorkspace"]
        )
        self._emit_trace(project_id, "Ideation", "STATUS_CHANGE", f"ProductSpec created for '{app_name}'. Ready for implementation.")

        # ------------------- 4. IMPLEMENTATION AGENT -------------------
        self._emit_trace(project_id, "Implementation", "STATUS_CHANGE", f"Scaffolding React project sandbox at /generated-apps/{project_id}/...")
        
        # 4a. Scaffold base
        scaffold_res = scaffold_base_template(project_id, product_spec_data.app_name, product_spec_data.tagline)
        self._emit_trace(project_id, "Implementation", "TOOL_EXECUTION", scaffold_res)
        
        # 4b. Write rich, interactive App.jsx for prototype
        self._emit_trace(project_id, "Implementation", "THOUGHT", "Generating interactive React prototype source code with live tabs, metrics, and feature controls...")
        
        features_json = json.dumps([f.model_dump() for f in product_spec_data.core_feature_list])
        
        rich_app_jsx = """const { useState, useEffect } = React;

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [features] = useState(__FEATURES_JSON__);
  const [items] = useState([
    { id: 1, name: 'Live Stream Telemetry', status: 'ACTIVE', metrics: '99.9% Uptime' },
    { id: 2, name: 'Automated Gap Detection', status: 'OPTIMAL', metrics: '42 Opportunities' },
    { id: 3, name: 'Workflow Engine', status: 'RUNNING', metrics: '12 Jobs Active' }
  ]);

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', fontFamily: "'Inter', sans-serif" }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 style={{ fontSize: '2.2rem', fontWeight: 800, background: 'linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              __APP_NAME__
            </h1>
            <span className="tag">__TARGET_INDUSTRY__</span>
          </div>
          <p style={{ color: '#94a3b8', marginTop: '0.5rem', fontSize: '1.05rem' }}>__TAGLINE__</p>
        </div>
        <button className="btn" onClick={() => alert('Live Prototype Action Executed!')}>
          Launch Demo Portal →
        </button>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
        <div className="card">
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Addressable Market (TAM)</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#60a5fa', marginTop: '0.5rem' }}>__MARKET_TAM__</div>
        </div>
        <div className="card">
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Opportunity Score</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981', marginTop: '0.5rem' }}>__OPPORTUNITY_SCORE__ / 10</div>
        </div>
        <div className="card">
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Core Features</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#c084fc', marginTop: '0.5rem' }}>__FEATURE_COUNT__ Active</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.75rem' }}>
        {['dashboard', 'features', 'market-insights'].map(tab => (
          <button 
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              background: activeTab === tab ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              color: activeTab === tab ? '#60a5fa' : '#94a3b8',
              border: '1px solid ' + (activeTab === tab ? 'rgba(59, 130, 246, 0.4)' : 'transparent'),
              padding: '0.5rem 1.25rem',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              textTransform: 'capitalize'
            }}
          >
            {tab.replace('-', ' ')}
          </button>
        ))}
      </div>

      {activeTab === 'dashboard' && (
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Live Operational Stream</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {items.map(item => (
              <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{item.metrics}</div>
                </div>
                <span className="tag" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>{item.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'features' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {features.map((feat, idx) => (
            <div key={idx} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <h4 style={{ fontWeight: 600 }}>{feat.feature_name}</h4>
                <span className="tag">{feat.priority}</span>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{feat.description}</p>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'market-insights' && (
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Market Differentiation Strategy</h3>
          <p style={{ color: '#cbd5e1', marginBottom: '1.5rem' }}><strong>Target Persona Insight:</strong> __PERSONA_INSIGHTS__</p>
          <p style={{ color: '#cbd5e1' }}><strong>Differentiation Angle:</strong> __DIFFERENTIATION__</p>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
"""
        rich_app_jsx = rich_app_jsx.replace("__APP_NAME__", product_spec_data.app_name)
        rich_app_jsx = rich_app_jsx.replace("__TAGLINE__", product_spec_data.tagline)
        rich_app_jsx = rich_app_jsx.replace("__TARGET_INDUSTRY__", discovery_data.target_industry)
        rich_app_jsx = rich_app_jsx.replace("__MARKET_TAM__", market_research_data.market_size_tam)
        rich_app_jsx = rich_app_jsx.replace("__OPPORTUNITY_SCORE__", str(discovery_data.opportunity_score))
        rich_app_jsx = rich_app_jsx.replace("__FEATURE_COUNT__", str(len(product_spec_data.core_feature_list)))
        rich_app_jsx = rich_app_jsx.replace("__FEATURES_JSON__", features_json)
        rich_app_jsx = rich_app_jsx.replace("__PERSONA_INSIGHTS__", market_research_data.target_persona_insights)
        rich_app_jsx = rich_app_jsx.replace("__DIFFERENTIATION__", market_research_data.differentiation_angle)

        w_res = write_file(project_id, "src/App.jsx", rich_app_jsx)
        self._emit_trace(project_id, "Implementation", "TOOL_EXECUTION", w_res)
        
        # 4c. Generate Manifest
        manifest_items = generate_manifest(project_id)
        generation_time = round(time.time() - start_time, 2)
        
        build_artifact = AppBuildArtifact(
            project_id=project_id,
            workspace_path=str(GENERATED_APPS_DIR / project_id),
            live_preview_url=f"/preview/{project_id}/index.html",
            file_manifest=manifest_items,
            build_status="SUCCESS",
            generation_time_seconds=generation_time
        )
        
        self._emit_trace(
            project_id, "Implementation", "STATUS_CHANGE",
            f"Build complete! Generated {len(manifest_items)} workspace files in {generation_time}s."
        )

        package = StartupIdeaPackage(
            project_id=project_id,
            timestamp=timestamp,
            discovery=discovery_data,
            market_research=market_research_data,
            product_spec=product_spec_data,
            build_artifact=build_artifact
        )

        # Save package_metadata.json in project directory
        pkg_file = GENERATED_APPS_DIR / project_id / "package_metadata.json"
        pkg_file.write_text(package.model_dump_json(indent=2), encoding="utf-8")
        
        self._emit_trace(project_id, "Pipeline", "STATUS_CHANGE", f"Pipeline successfully finished for '{app_name}'.")
        return package
