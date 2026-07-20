import asyncio
from typing import Dict, Any, Optional

class HumanInTheLoopManager:
    """
    Human-in-the-loop (HITL) confirmation manager for multi-agent pipeline workflow execution.
    Allows critical pipeline actions (such as product spec approval before code generation)
    to wait for human approval or proceed automatically based on system mode.
    """
    def __init__(self, require_approval: bool = False):
        self.require_approval = require_approval
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.approved_projects: Dict[str, bool] = {}

    def request_approval(self, project_id: str, step_name: str, payload: Dict[str, Any]) -> str:
        approval_id = f"hitl-{project_id}-{step_name}"
        self.pending_approvals[approval_id] = {
            "project_id": project_id,
            "step_name": step_name,
            "payload": payload,
            "status": "PENDING"
        }
        return approval_id

    def approve_step(self, approval_id: str) -> bool:
        if approval_id in self.pending_approvals:
            self.pending_approvals[approval_id]["status"] = "APPROVED"
            project_id = self.pending_approvals[approval_id]["project_id"]
            self.approved_projects[project_id] = True
            return True
        return False

    async def wait_for_approval(self, project_id: str, step_name: str, payload: Dict[str, Any], timeout_seconds: int = 5) -> bool:
        if not self.require_approval:
            return True # Auto-approve if HITL mode is disabled

        approval_id = self.request_approval(project_id, step_name, payload)
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            if self.pending_approvals.get(approval_id, {}).get("status") == "APPROVED":
                return True
            await asyncio.sleep(0.5)

        # Default fallback auto-approve after timeout for unattended runs
        self.pending_approvals[approval_id]["status"] = "AUTO_APPROVED_TIMEOUT"
        return True

hitl_manager = HumanInTheLoopManager(require_approval=False)
