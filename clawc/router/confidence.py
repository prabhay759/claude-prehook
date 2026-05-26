from __future__ import annotations

from enum import Enum


class RouteDecision(Enum):
    SAFE = "safe"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


def route(content: str, pressure: float = 0.0) -> RouteDecision:
    from clawc.pipeline.safemode import is_unsafe

    if is_unsafe(content):
        return RouteDecision.SAFE
    if pressure >= 0.8:
        return RouteDecision.AGGRESSIVE
    return RouteDecision.NORMAL
