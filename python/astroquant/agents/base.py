"""Structured logging + the Agent contract (per docs/004_AGENT_ARCHITECTURE.md)."""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@dataclass
class RunContext:
    """Inputs to an agent run."""
    run_id: str
    start: date | None = None
    end: date | None = None
    symbols: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    seed: int = 42


@dataclass
class RunResult:
    """Outputs of an agent run. Always reproducible from the manifest."""
    agent: str
    status: str                      # ok | failed
    rows_written: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    output_hashes: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    manifest_path: str | None = None

    def write_manifest(self, ctx: RunContext, code_commit: str = "uncommitted") -> str:
        """Persist a run manifest so any result is reproducible (docs/000 §6)."""
        manifest = {
            "agent": self.agent,
            "run_id": ctx.run_id,
            "status": self.status,
            "start": str(ctx.start),
            "end": str(ctx.end),
            "symbols": ctx.symbols,
            "config": ctx.config,
            "seed": ctx.seed,
            "rows_written": self.rows_written,
            "metrics": self.metrics,
            "output_hashes": self.output_hashes,
            "code_commit": code_commit,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        out_dir = Path("manifests")
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"{self.agent}_{ctx.run_id}.json"
        path.write_text(json.dumps(manifest, indent=2))
        self.manifest_path = str(path)
        return self.manifest_path


@dataclass
class Health:
    ok: bool
    detail: str = ""


class Agent(Protocol):
    """Every agent implements this. Runs MUST be idempotent (re-runs heal, never duplicate)."""
    name: str
    version: str

    def run(self, ctx: RunContext) -> RunResult: ...
    def healthcheck(self) -> Health: ...


def content_hash(obj: Any) -> str:
    """Stable hash for provenance stamping of datasets/outputs."""
    payload = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:16]
