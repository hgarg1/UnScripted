from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentTurnContext:
    agent_id: str
    handle: str
    archetype: str
    influence_score: float
    available_budget_tokens: int
    pending_mentions: int
    recent_engagement: int
    trust_delta: float = 0.0
    hostility_delta: float = 0.0
    target_topic: str | None = None
    dominant_memory: str | None = None


@dataclass(frozen=True, slots=True)
class AgentTurnPlan:
    action: str
    confidence: float
    should_generate_text: bool
    reason: str


def plan_turn(context: AgentTurnContext) -> AgentTurnPlan:
    if context.available_budget_tokens <= 0:
        return AgentTurnPlan(
            action="disengage",
            confidence=1.0,
            should_generate_text=False,
            reason="budget exhausted",
        )
    if context.pending_mentions > 0 and context.trust_delta >= 0:
        return AgentTurnPlan(
            action="reply",
            confidence=0.82,
            should_generate_text=True,
            reason="mentions pending and trust is non-negative",
        )
    if context.hostility_delta > 0.6:
        return AgentTurnPlan(
            action="escalate",
            confidence=0.73,
            should_generate_text=True,
            reason="hostility threshold exceeded",
        )
    if context.recent_engagement < 2 and context.influence_score < 0.15:
        return AgentTurnPlan(
            action="like",
            confidence=0.68,
            should_generate_text=False,
            reason="low reach agents amplify before posting",
        )
    if context.recent_engagement >= 3 and context.influence_score < 0.4:
        return AgentTurnPlan(
            action="follow",
            confidence=0.62,
            should_generate_text=False,
            reason="engagement suggests network expansion",
        )
    return AgentTurnPlan(
        action="post",
        confidence=0.76,
        should_generate_text=True,
        reason="default cadence favors original posting",
    )


def generate_text(context: AgentTurnContext, plan: AgentTurnPlan) -> str:
    topic = context.target_topic or "the shape of the discourse"
    memory = context.dominant_memory or "the timeline keeps drifting"
    handle = f"@{context.handle}"

    if plan.action == "reply":
        return f"{handle} keeps circling back to {topic}. {memory}."
    if plan.action == "escalate":
        return f"{handle} thinks the consensus around {topic} looks manufactured, not earned."
    if plan.action == "post":
        if context.archetype == "contrarian":
            return f"If everyone agrees on {topic}, {handle} assumes coordination before truth."
        if context.archetype == "bridge-builder":
            return f"{handle} sees {topic} as a systems problem: ranking, repetition, and memory loops."
        if context.archetype == "booster":
            return f"{handle} says {topic} is already moving. Amplification does the rest."
        return f"{handle} is thinking about {topic}. {memory}."
    return ""


def estimate_token_cost(plan: AgentTurnPlan, generated_text: str) -> int:
    if not plan.should_generate_text:
        return 20
    return max(60, len(generated_text.split()) * 12)
