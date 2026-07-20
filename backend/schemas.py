import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class CompetitorInfo(BaseModel):
    name: str
    url: str = ""
    key_weakness: str
    market_share_estimate: str = "Unknown"

class FeatureSpec(BaseModel):
    feature_name: str
    description: str
    priority: str = "HIGH"  # HIGH, MEDIUM, LOW

class UIUXRequirements(BaseModel):
    color_palette: List[str] = Field(default_factory=lambda: ["#0f172a", "#3b82f6", "#10b981", "#f8fafc"])
    layout_style: str = "Modern SaaS Application"
    typography_vibe: str = "Clean Sans-Serif"

class DiscoveryResult(BaseModel):
    project_id: str
    timestamp: str
    target_industry: str
    uncovered_pain_point: str
    target_demographic: str
    opportunity_score: float = Field(ge=1.0, le=10.0)
    search_queries_used: List[str] = Field(default_factory=list)

class MarketResearchReport(BaseModel):
    project_id: str
    competitors: List[CompetitorInfo] = Field(default_factory=list)
    market_size_tam: str
    market_size_sam: str
    key_market_trends: List[str] = Field(default_factory=list)
    target_persona_insights: str
    differentiation_angle: str

class ProductSpec(BaseModel):
    project_id: str
    app_name: str
    tagline: str
    value_proposition: str
    core_feature_list: List[FeatureSpec] = Field(default_factory=list)
    ui_ux_requirements: UIUXRequirements = Field(default_factory=UIUXRequirements)
    data_model_sketch: List[str] = Field(default_factory=list)

class FileManifestItem(BaseModel):
    file_path: str
    file_size_bytes: int
    file_type: str

class AppBuildArtifact(BaseModel):
    project_id: str
    workspace_path: str
    live_preview_url: str
    file_manifest: List[FileManifestItem] = Field(default_factory=list)
    build_status: str = "SUCCESS"  # SUCCESS, PARTIAL, FAILED
    generation_time_seconds: float = 0.0

class TraceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    project_id: str
    agent_name: str  # Discovery, MarketResearch, Ideation, Implementation, System
    event_type: str  # THOUGHT, TOOL_QUERY, TOOL_EXECUTION, STATUS_CHANGE
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PipelineStatusResponse(BaseModel):
    is_pipeline_active: bool
    execution_count: int
    last_run_timestamp: Optional[str] = None
    current_run_project_id: Optional[str] = None
    next_scheduled_run: Optional[str] = None

class StartupIdeaPackage(BaseModel):
    project_id: str
    timestamp: str
    discovery: DiscoveryResult
    market_research: MarketResearchReport
    product_spec: ProductSpec
    build_artifact: Optional[AppBuildArtifact] = None
