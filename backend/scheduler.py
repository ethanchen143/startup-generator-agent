import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.agents.pipeline import PipelineRunner
from backend.schemas import StartupIdeaPackage, TraceEvent

logger = logging.getLogger("pipeline_scheduler")

class PipelineScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_pipeline_active: bool = True
        self.execution_count: int = 0
        self.last_run_timestamp: Optional[str] = None
        self.current_run_project_id: Optional[str] = None
        self.websocket_listeners: List[Any] = []
        self._lock = asyncio.Lock()

    def add_listener(self, websocket):
        self.websocket_listeners.append(websocket)

    def remove_listener(self, websocket):
        if websocket in self.websocket_listeners:
            self.websocket_listeners.remove(websocket)

    async def broadcast_trace(self, trace_event: TraceEvent):
        payload = trace_event.model_dump_json()
        to_remove = []
        for ws in self.websocket_listeners:
            try:
                await ws.send_text(payload)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self.remove_listener(ws)

    async def trigger_pipeline(self, is_manual: bool = False) -> Optional[StartupIdeaPackage]:
        if not self.is_pipeline_active and not is_manual:
            logger.info("Pipeline execution skipped because scheduler is paused.")
            return None

        async with self._lock:
            self.execution_count += 1
            self.last_run_timestamp = datetime.utcnow().isoformat()
            
            runner = PipelineRunner(trace_callback=self.broadcast_trace)
            try:
                package = await runner.execute_pipeline()
                return package
            except Exception as e:
                logger.error(f"Error during pipeline execution: {e}")
                return None

    def start(self):
        # Schedule cron at top of every hour (0 * * * *)
        self.scheduler.add_job(
            self.trigger_pipeline,
            CronTrigger(minute=0),
            id="hourly_pipeline_job",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("APScheduler started with hourly cron trigger (0 * * * *).")

    def stop(self):
        self.scheduler.shutdown(wait=False)

pipeline_scheduler = PipelineScheduler()
