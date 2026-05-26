from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RoutingDecision:
    suggested_model: str
    reason: str
    complexity_score: float


def suggest_model(content: str, task_description: str = "") -> RoutingDecision:
    score = _complexity_score(content, task_description)
    if score < 0.3:
        return RoutingDecision("claude-haiku-4-5", "simple/repetitive content", score)
    elif score < 0.7:
        return RoutingDecision("claude-sonnet-4-6", "moderate complexity", score)
    else:
        return RoutingDecision("claude-opus-4-7", "complex reasoning required", score)


def _complexity_score(content: str, task: str) -> float:
    score = 0.0
    for kw in ["class ", "def ", "async ", "await ", "lambda ", "yield "]:
        if kw in content:
            score += 0.05
    for kw in ["debug", "refactor", "architect", "design", "analyze", "explain why"]:
        if kw.lower() in task.lower():
            score += 0.15
    return min(1.0, score)
