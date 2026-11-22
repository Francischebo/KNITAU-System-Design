from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
import uuid


@dataclass(frozen=True)
class DomainEvent:
    """Base contract for in-process domain events decoupling bounded modules."""

    event_name: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_SUBSCRIBERS: dict[str, list[Callable[[DomainEvent], None]]] = defaultdict(list)


def subscribe_event(event_name: str, handler: Callable[[DomainEvent], None]) -> None:
    if handler not in _SUBSCRIBERS[event_name]:
        _SUBSCRIBERS[event_name].append(handler)


def publish_event(event: DomainEvent) -> None:
    for handler in _SUBSCRIBERS.get(event.event_name, ()):
        handler(event)
