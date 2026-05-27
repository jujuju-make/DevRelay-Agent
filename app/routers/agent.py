from fastapi import APIRouter

from app.schemas.agent import AgentRunRequest, AgentRunResponse, ArchiveDecisionRequest
from app.services.agent_graph import run_agent_with_archive, handle_archive_response

router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
async def run_agent_endpoint(body: AgentRunRequest) -> AgentRunResponse:
    result = await run_agent_with_archive(
        body.query,
        session_id=body.session_id,
        repo_owner=body.repo_owner,
        repo_name=body.repo_name,
    )
    return AgentRunResponse(**result)


@router.post("/archive-decision", response_model=AgentRunResponse)
async def archive_decision_endpoint(body: ArchiveDecisionRequest) -> AgentRunResponse:
    result = await handle_archive_response(
        session_id=body.session_id,
        decision=body.decision,
    )
    return AgentRunResponse(**result)
