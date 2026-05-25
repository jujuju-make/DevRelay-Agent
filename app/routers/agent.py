from fastapi import APIRouter

from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.agent_logic import run_agent

router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
async def run_agent_endpoint(body: AgentRunRequest) -> AgentRunResponse:
    result = await run_agent(
        body.query,
        session_id=body.session_id,
        repo_owner=body.repo_owner,
        repo_name=body.repo_name,
    )
    return AgentRunResponse(**result)
