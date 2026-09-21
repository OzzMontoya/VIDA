"""Contratos entre agente y mundo: percepción, propuesta de acción y resultado.

- ``PerceptionSnapshot``: lo que el agente ve en su ubicación este tick.
- ``ActionProposal``: intención del agente. ``rationale`` es texto libre para
  trazabilidad; **el mundo nunca lo lee** (principio 3 del proyecto).
- ``ActionOutcome``: consecuencia objetiva resuelta por el mundo. Es la única
  fuente de verdad para actualizar necesidades, memoria y relaciones.
- ``InfoRequest`` / ``InfoReply``: mecanismo de intercambio de información que
  habilita el experimento de engaño (sección 20).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ActionKind = Literal[
    "move", "acquire", "consume", "work", "rest", "socialize",
    "ask_info", "share_info", "study", "seek_care", "idle",
]
ACTION_KINDS: tuple[ActionKind, ...] = (
    "move", "acquire", "consume", "work", "rest", "socialize",
    "ask_info", "share_info", "study", "seek_care", "idle",
)

OutcomeKind = Literal[
    "ok", "blocked", "closed", "resource_absent", "insufficient_funds",
    "rejected", "no_reply", "illegal",
]

ReplyKind = Literal["truth", "lie", "omit", "partial"]


class PerceptionSnapshot(BaseModel):
    tick: int
    hour: int
    location_id: str
    location_type: str
    is_open: bool
    visible_agents: list[str] = Field(default_factory=list)
    visible_resources: dict[str, int] = Field(default_factory=dict)
    prices: dict[str, float] = Field(default_factory=dict)
    recent_public_events: list[str] = Field(default_factory=list)


class InfoRequest(BaseModel):
    asker_id: str
    responder_id: str
    resource: str
    tick: int


class InfoReply(BaseModel):
    """Respuesta de un agente a una petición de información.

    ``kind`` es la *intención* del que responde. El agente que pregunta no la
    recibe: sólo recibe ``claimed_location`` (o nada si ``omit``).
    """

    responder_id: str
    resource: str
    kind: ReplyKind
    claimed_location: str | None = None
    claimed_confidence: float = 1.0


class ActionProposal(BaseModel):
    kind: ActionKind
    target_location: str | None = None
    target_agent: str | None = None
    resource: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""

    def key(self) -> str:
        """Clave canónica y ordenable: ``consume:bread``, ``socialize->a02``, ``move@market``."""
        key = str(self.kind)
        if self.resource:
            key += f":{self.resource}"
        if self.target_agent:
            key += f"->{self.target_agent}"
        if self.target_location:
            key += f"@{self.target_location}"
        return key


class ActionOutcome(BaseModel):
    tick: int
    agent_id: str
    action: ActionKind
    kind: OutcomeKind
    success: bool
    location_id: str
    resource: str | None = None
    target_agent: str | None = None
    new_location: str | None = None
    need_deltas: dict[str, float] = Field(default_factory=dict)
    inventory_deltas: dict[str, int] = Field(default_factory=dict)
    money_delta: float = 0.0
    other_need_deltas: dict[str, dict[str, float]] = Field(default_factory=dict)
    valence: float = 0.0  # signo del resultado para el agente, fijado por el mundo
    details: dict[str, Any] = Field(default_factory=dict)
    world_delta: dict[str, Any] = Field(default_factory=dict)

    def key(self) -> str:
        return f"{self.action}:{self.kind}"
