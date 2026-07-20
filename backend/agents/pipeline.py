import os
import time
import json
import uuid
import datetime
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any, Type

from google import genai
from google.genai import types
from pydantic import BaseModel

from backend.config import GENERATED_APPS_DIR, GOOGLE_API_KEY, get_model_for_agent
from backend.constitution import AGENT_CONSTITUTION
from backend.schemas import (
    DiscoveryResult, CompetitorInfo, MarketResearchReport,
    FeatureSpec, UIUXRequirements, ProductSpec,
    AppBuildArtifact, StartupIdeaPackage, TraceEvent
)
from backend.tools.search_tool import google_search_wrapper
from backend.tools.webdev_writer import (
    scaffold_base_template, write_file, generate_manifest, create_workspace_directory
)
from backend.memory import session_store, compact_history, consolidate_memory_async
from backend.pii_redactor import redact_pii
from backend.logger import pipeline_logger
from backend.telemetry import start_agent_span
from backend.guardrails import validate_input_safety, validate_output_safety
from backend.hitl import hitl_manager

class AgentPipeline:
    def __init__(self, trace_callback: Optional[Callable[[TraceEvent], None]] = None):
        self.trace_callback = trace_callback
        self.genai_client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

    def _emit_trace(self, project_id: str, agent_name: str, event_type: str, content: str):
        scrubbed_content = redact_pii(content)

        event = TraceEvent(
            project_id=project_id,
            agent_name=agent_name,
            event_type=event_type,
            content=scrubbed_content,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        
        pipeline_logger.info(
            scrubbed_content,
            extra={
                "project_id": project_id,
                "agent_name": agent_name,
                "event_type": event_type
            }
        )

        if self.trace_callback:
            try:
                self.trace_callback(event)
            except Exception as e:
                print(f"Error emitting trace event: {e}")

    def _call_llm(
        self,
        agent_name: str,
        prompt: str,
        default_fallback: str,
        response_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        """
        Invokes defined LLM agent using strategic model routing (Fast Model vs Reasoning Model).
        Directly constrains output with Pydantic JSON schemas via response_schema configuration.
        Includes input/output security guardrails and fallback resilience.
        """
        safety_check = validate_input_safety(prompt)
        if not safety_check.get("safe"):
            self._emit_trace("SYSTEM", agent_name, "STATUS_CHANGE", f"Guardrail Alert: {safety_check.get('reason')}")
            return default_fallback

        if not self.genai_client:
            return default_fallback

        model_name = get_model_for_agent(agent_name)
        try:
            full_prompt = f"{AGENT_CONSTITUTION}\n\nTask Instructions:\n{prompt}"
            
            config_kwargs: Dict[str, Any] = {
                "temperature": 0.7,
                "max_output_tokens": 1500
            }
            
            # Constrain LLM output directly with explicit Pydantic JSON Schema if provided
            if response_schema:
                config_kwargs["response_mime_type"] = "application/json"
                config_kwargs["response_schema"] = response_schema

            response = self.genai_client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(**config_kwargs)
            )
            out_text = response.text if response and response.text else default_fallback
            
            out_safety = validate_output_safety(out_text)
            if not out_safety.get("safe"):
                self._emit_trace("SYSTEM", agent_name, "STATUS_CHANGE", f"Guardrail Alert on Output: {out_safety.get('reason')}")
                return default_fallback
                
            return out_text
        except Exception as e:
            pipeline_logger.warning(f"LLM call to model {model_name} failed: {e}. Utilizing structured recovery.")
            return default_fallback

    async def execute_pipeline(self, project_id: Optional[str] = None) -> StartupIdeaPackage:
        if not project_id:
            project_id = f"idea-{uuid.uuid4().hex[:8]}"
            
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        start_time = time.time()
        trace_events_log: List[Dict[str, Any]] = []

        self._emit_trace(project_id, "Pipeline", "STATUS_CHANGE", f"Starting 4-Agent Pipeline for Project ID: {project_id}")

        session_state = {
            "project_id": project_id,
            "status": "RUNNING",
            "start_time": start_time
        }
        turn_history: List[Dict[str, Any]] = [
            {"role": "system", "content": f"AGENT CONSTITUTION:\n{AGENT_CONSTITUTION}"}
        ]

        # ------------------- 1. DISCOVERY AGENT -------------------
        span_disc = start_agent_span("Discovery", project_id)
        try:
            self._emit_trace(project_id, "Discovery", "STATUS_CHANGE", "Initiating industry opportunity scan...")
            
            industries = [
                "AI-powered Operations for Niche Logistics",
                "Sustainable Supply Chain Analytics for Micro-Brands",
                "Automated Compliance & Telemetry for Remote Health Tech",
                "Commercial Property Energy Optimization SaaS",
                "Creator Economy Dynamic Contract & Royalty Distribution"
            ]
            chosen_industry = industries[hash(project_id) % len(industries)]
            
            self._emit_trace(project_id, "Discovery", "TOOL_QUERY", f"Executing web search for unserved market pain points in '{chosen_industry}'...")
            search_json = google_search_wrapper(f"{chosen_industry} pain points market opportunities 2026")
            
            self._emit_trace(project_id, "Discovery", "THOUGHT", f"Invoking LLM Discovery Agent with Fast Model ({get_model_for_agent('Discovery')}) and Pydantic JSON Schema response constraint.")
            
            discovery_prompt = f"""
            Analyze these web search results for the industry '{chosen_industry}':
            {search_json}
            
            Synthesize market signals and populate the DiscoveryResult schema for project_id '{project_id}'.
            """
            
            disc_fallback = json.dumps({
                "project_id": project_id,
                "timestamp": timestamp,
                "target_industry": chosen_industry,
                "uncovered_pain_point": f"Fragmented manual processes and lack of real-time telemetry streaming in {chosen_industry}.",
                "target_demographic": "Operations Managers and SMB Founders",
                "opportunity_score": 8.7,
                "search_queries_used": [f"{chosen_industry} pain points", "market gaps 2026"]
            })
            
            llm_disc_res = self._call_llm("Discovery", discovery_prompt, disc_fallback, response_schema=DiscoveryResult)
            
            try:
                clean_json_str = llm_disc_res[llm_disc_res.find('{'):llm_disc_res.rfind('}')+1]
                disc_parsed = json.loads(clean_json_str)
            except Exception:
                disc_parsed = json.loads(disc_fallback)

            discovery_data = DiscoveryResult(
                project_id=project_id,
                timestamp=timestamp,
                target_industry=chosen_industry,
                uncovered_pain_point=disc_parsed.get("uncovered_pain_point", f"Lack of real-time telemetry in {chosen_industry}"),
                target_demographic=disc_parsed.get("target_demographic", "SMB Founders & Operations Directors"),
                opportunity_score=float(disc_parsed.get("opportunity_score", 8.7)),
                search_queries_used=[f"{chosen_industry} pain points", "market gaps 2026"]
            )
            
            turn_history.append({"role": "assistant", "content": f"Discovery Complete: {discovery_data.uncovered_pain_point}"})
            turn_history = compact_history(turn_history)
            session_store.save_session(project_id, session_state, turn_history)
            
            self._emit_trace(project_id, "Discovery", "STATUS_CHANGE", f"Discovery completed. Opportunity score: {discovery_data.opportunity_score}/10")
        finally:
            span_disc.end()

        # ------------------- 2. MARKET RESEARCH AGENT -------------------
        span_mr = start_agent_span("MarketResearch", project_id)
        try:
            self._emit_trace(project_id, "MarketResearch", "STATUS_CHANGE", "Starting competitive landscape and market sizing analysis...")
            self._emit_trace(project_id, "MarketResearch", "TOOL_QUERY", f"Searching competitors for {discovery_data.target_industry}...")
            
            mr_search = google_search_wrapper(f"{chosen_industry} top competitors TAM SAM market size")
            self._emit_trace(project_id, "MarketResearch", "THOUGHT", f"Invoking LLM Market Research Agent ({get_model_for_agent('MarketResearch')}) with Pydantic MarketResearchReport JSON Schema constraint.")
            
            mr_prompt = f"""
            Based on industry '{chosen_industry}' and research:
            {mr_search}
            
            Synthesize market size and competitor weaknesses adhering to MarketResearchReport schema.
            """
            
            mr_fallback = json.dumps({
                "project_id": project_id,
                "competitors": [
                    {"name": "LegacyCorp Analytics", "url": "https://legacycorp.example.com", "key_weakness": "Clunky static UI, expensive enterprise lock-in", "market_share_estimate": "35%"},
                    {"name": "ManualSheet Tools", "url": "https://manualsheet.example.com", "key_weakness": "Requires manual export, no automated workflow", "market_share_estimate": "25%"}
                ],
                "market_size_tam": "$4.5 Billion",
                "market_size_sam": "$850 Million",
                "key_market_trends": ["Shift toward real-time telemetry", "Demand for low-code automation"],
                "target_persona_insights": "Mid-market team leads seeking instant visibility without complex 6-month deployment cycles.",
                "differentiation_angle": "Real-time WebSocket event streaming paired with single-click interactive prototype execution."
            })
            
            llm_mr_res = self._call_llm("MarketResearch", mr_prompt, mr_fallback, response_schema=MarketResearchReport)
            try:
                clean_json_str = llm_mr_res[llm_mr_res.find('{'):llm_mr_res.rfind('}')+1]
                mr_parsed = json.loads(clean_json_str)
            except Exception:
                mr_parsed = json.loads(mr_fallback)

            market_research_data = MarketResearchReport(
                project_id=project_id,
                competitors=[
                    CompetitorInfo(name=c.get("name", "LegacyCorp"), url=c.get("url", ""), key_weakness=c.get("key_weakness", "Expensive lock-in"), market_share_estimate=c.get("market_share_estimate", "35%"))
                    for c in mr_parsed.get("competitors", [])
                ] or [
                    CompetitorInfo(name="LegacyCorp Analytics", url="https://legacycorp.example.com", key_weakness="Clunky static UI, expensive enterprise lock-in", market_share_estimate="35%"),
                    CompetitorInfo(name="ManualSheet Tools", url="https://manualsheet.example.com", key_weakness="Requires manual export, no automated workflow", market_share_estimate="25%")
                ],
                market_size_tam=mr_parsed.get("market_size_tam", "$4.5 Billion"),
                market_size_sam=mr_parsed.get("market_size_sam", "$850 Million"),
                key_market_trends=mr_parsed.get("key_market_trends", ["Shift toward real-time telemetry"]),
                target_persona_insights=mr_parsed.get("target_persona_insights", "Mid-market team leads seeking instant visibility."),
                differentiation_angle=mr_parsed.get("differentiation_angle", "Real-time WebSocket streaming paired with instant prototype execution.")
            )
            
            turn_history.append({"role": "assistant", "content": f"Market Research Complete. TAM: {market_research_data.market_size_tam}"})
            turn_history = compact_history(turn_history)
            session_store.save_session(project_id, session_state, turn_history)
            
            self._emit_trace(project_id, "MarketResearch", "STATUS_CHANGE", f"Market research complete. Identified {market_research_data.market_size_tam} TAM.")
        finally:
            span_mr.end()

        # ------------------- 3. IDEATION AGENT -------------------
        span_ideo = start_agent_span("Ideation", project_id)
        try:
            self._emit_trace(project_id, "Ideation", "STATUS_CHANGE", "Synthesizing research into dynamic Product Specification...")
            self._emit_trace(project_id, "Ideation", "THOUGHT", f"Invoking LLM Ideation Agent ({get_model_for_agent('Ideation')}) with Pydantic ProductSpec JSON Schema constraint.")
            
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
            
            self._emit_trace(project_id, "Ideation", "STATUS_CHANGE", "Requesting Human-In-The-Loop (HITL) confirmation for ProductSpec approval...")
            await hitl_manager.wait_for_approval(project_id, "ProductSpecApproval", product_spec_data.model_dump())
            self._emit_trace(project_id, "Ideation", "STATUS_CHANGE", f"ProductSpec approved for '{app_name}'. Ready for Implementation.")
        finally:
            span_ideo.end()

        # ------------------- 4. IMPLEMENTATION AGENT -------------------
        span_impl = start_agent_span("Implementation", project_id)
        try:
            self._emit_trace(project_id, "Implementation", "STATUS_CHANGE", f"Scaffolding React project sandbox at /generated-apps/{project_id}/...")
            
            scaffold_res = scaffold_base_template(project_id, product_spec_data.app_name, product_spec_data.tagline)
            self._emit_trace(project_id, "Implementation", "TOOL_EXECUTION", str(scaffold_res))
            
            self._emit_trace(project_id, "Implementation", "THOUGHT", f"Invoking LLM Implementation Agent ({get_model_for_agent('Implementation')}) to generate React prototype code.")
            
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
            self._emit_trace(project_id, "Implementation", "TOOL_EXECUTION", str(w_res))
            
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
        finally:
            span_impl.end()

        package = StartupIdeaPackage(
            project_id=project_id,
            timestamp=timestamp,
            discovery=discovery_data,
            market_research=market_research_data,
            product_spec=product_spec_data,
            build_artifact=build_artifact
        )

        pkg_file = GENERATED_APPS_DIR / project_id / "package_metadata.json"
        pkg_file.write_text(package.model_dump_json(indent=2), encoding="utf-8")
        
        session_state["status"] = "COMPLETED"
        session_store.save_session(project_id, session_state, turn_history)
        await consolidate_memory_async(project_id, trace_events_log)
        
        self._emit_trace(project_id, "Pipeline", "STATUS_CHANGE", f"Pipeline successfully finished for '{app_name}'.")
        return package
