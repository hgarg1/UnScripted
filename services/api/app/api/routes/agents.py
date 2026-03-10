from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole
from services.api.app.models.agent import (
    Agent,
    AgentCohort,
    AgentCohortMembership,
    AgentMemory,
    AgentPromptVersion,
    AgentTurnLog,
)
from services.api.app.models.social import User
from services.api.app.schemas.agents import (
    AgentCohortResponse,
    AgentExecutionResponse,
    AgentListResponse,
    AgentMemoryResponse,
    AgentMemoriesResponse,
    AgentPromptVersionResponse,
    AgentResponse,
    AgentTurnLogResponse,
    AgentTurnLogsResponse,
    AssignAgentCohortRequest,
    CreateAgentCohortRequest,
    CreateAgentPromptVersionRequest,
    CreateAgentRequest,
    ExecuteAgentTurnRequest,
)
from services.api.app.services.agents import create_agent, list_agents
from services.api.app.services.auth import get_current_user
from services.api.app.services.simulation import run_agent_turn_job

router = APIRouter(prefix="/v1/admin", tags=["agents"])


def _require_admin(user: User) -> None:
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")


@router.get("/agent-prompts", response_model=list[AgentPromptVersionResponse])
def get_agent_prompts(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[AgentPromptVersionResponse]:
    _require_admin(current_user)
    rows = list(
        session.scalars(select(AgentPromptVersion).order_by(AgentPromptVersion.created_at.desc()))
    )
    session.commit()
    return [AgentPromptVersionResponse.model_validate(row) for row in rows]


@router.post("/agent-prompts", response_model=AgentPromptVersionResponse, status_code=status.HTTP_201_CREATED)
def create_agent_prompt(
    payload: CreateAgentPromptVersionRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentPromptVersionResponse:
    _require_admin(current_user)
    latest = session.scalar(
        select(AgentPromptVersion)
        .where(AgentPromptVersion.name == payload.name)
        .order_by(AgentPromptVersion.version.desc())
    )
    next_version = (latest.version + 1) if latest else 1
    if payload.activate:
        for prompt in session.scalars(select(AgentPromptVersion).where(AgentPromptVersion.name == payload.name)):
            prompt.is_active = False
    prompt = AgentPromptVersion(
        name=payload.name,
        version=next_version,
        system_prompt=payload.system_prompt,
        planning_notes=payload.planning_notes,
        style_guide=payload.style_guide,
        is_active=payload.activate,
    )
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return AgentPromptVersionResponse.model_validate(prompt)


@router.get("/agent-cohorts", response_model=list[AgentCohortResponse])
def get_agent_cohorts(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[AgentCohortResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(AgentCohort).order_by(AgentCohort.created_at.desc())))
    session.commit()
    return [AgentCohortResponse.model_validate(row) for row in rows]


@router.post("/agent-cohorts", response_model=AgentCohortResponse, status_code=status.HTTP_201_CREATED)
def create_agent_cohort(
    payload: CreateAgentCohortRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentCohortResponse:
    _require_admin(current_user)
    cohort = AgentCohort(
        name=payload.name,
        description=payload.description,
        scenario=payload.scenario,
        cadence_multiplier=payload.cadence_multiplier,
        budget_multiplier=payload.budget_multiplier,
    )
    session.add(cohort)
    session.commit()
    session.refresh(cohort)
    return AgentCohortResponse.model_validate(cohort)


@router.get("/agents", response_model=AgentListResponse)
def get_agents(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentListResponse:
    _require_admin(current_user)
    items = [AgentResponse(**item) for item in list_agents(session)]
    session.commit()
    return AgentListResponse(items=items)


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_admin_agent(
    payload: CreateAgentRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    _require_admin(current_user)
    try:
        agent = create_agent(
            session,
            handle=payload.handle,
            display_name=payload.display_name,
            archetype=payload.archetype,
            bio=payload.bio,
            prompt_version_id=payload.prompt_version_id,
            cohort_id=payload.cohort_id,
            belief_vector=payload.belief_vector,
            posts_per_day=payload.posts_per_day,
            daily_tokens=payload.daily_tokens,
            dm_enabled=payload.dm_enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    item = next(item for item in list_agents(session) if item["id"] == agent.id)
    session.commit()
    return AgentResponse(**item)


@router.post("/agents/{agent_id}/assign-cohort", response_model=AgentResponse)
def assign_agent_cohort(
    agent_id: str,
    payload: AssignAgentCohortRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    _require_admin(current_user)
    agent = session.get(Agent, agent_id)
    cohort = session.get(AgentCohort, payload.cohort_id)
    if not agent or not cohort:
        raise HTTPException(status_code=404, detail="agent or cohort not found")
    agent.primary_cohort_id = cohort.id
    membership = session.scalar(
        select(AgentCohortMembership).where(
            AgentCohortMembership.agent_id == agent.id,
            AgentCohortMembership.cohort_id == cohort.id,
        )
    )
    if not membership:
        session.add(AgentCohortMembership(agent_id=agent.id, cohort_id=cohort.id, role=payload.role))
    item = next(item for item in list_agents(session) if item["id"] == agent.id)
    session.commit()
    return AgentResponse(**item)


@router.post("/agents/{agent_id}/execute-turn", response_model=AgentExecutionResponse)
def execute_turn(
    agent_id: str,
    payload: ExecuteAgentTurnRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentExecutionResponse:
    _require_admin(current_user)
    try:
        _, result = run_agent_turn_job(
            session,
            agent_id=agent_id,
            requested_by=current_user.id,
            force_action=payload.force_action,
            target_topic=payload.target_topic,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return AgentExecutionResponse(
        log=AgentTurnLogResponse.model_validate(result.log),
        created_post_id=result.post_id,
        created_comment_id=result.comment_id,
        created_dm_id=result.dm_id,
        created_follow_target_id=result.follow_target_id,
        created_like_target_id=result.like_target_id,
    )


@router.get("/agents/{agent_id}/memories", response_model=AgentMemoriesResponse)
def get_agent_memories(
    agent_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentMemoriesResponse:
    _require_admin(current_user)
    rows = list(
        session.scalars(
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(AgentMemory.importance_score.desc(), AgentMemory.created_at.desc())
        )
    )
    session.commit()
    return AgentMemoriesResponse(items=[AgentMemoryResponse.model_validate(row) for row in rows])


@router.get("/agents/{agent_id}/turns", response_model=AgentTurnLogsResponse)
def get_agent_turns(
    agent_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentTurnLogsResponse:
    _require_admin(current_user)
    rows = list(
        session.scalars(
            select(AgentTurnLog)
            .where(AgentTurnLog.agent_id == agent_id)
            .order_by(AgentTurnLog.created_at.desc())
            .limit(50)
        )
    )
    session.commit()
    return AgentTurnLogsResponse(items=[AgentTurnLogResponse.model_validate(row) for row in rows])
