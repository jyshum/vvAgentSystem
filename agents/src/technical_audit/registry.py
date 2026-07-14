from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import CheckResult


Evaluator = Callable[[Any], list[CheckResult]]


@dataclass(frozen=True)
class CheckDefinition:
    id: str
    version: int
    section: str
    scope: str
    evaluator: Evaluator


class CheckRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, int], CheckDefinition] = {}

    def register(self, definition: CheckDefinition) -> None:
        key = (definition.id, definition.version)
        if key in self._definitions:
            raise ValueError(f"duplicate check version: {definition.id}@{definition.version}")
        self._definitions[key] = definition

    def definitions(self) -> tuple[CheckDefinition, ...]:
        return tuple(
            definition
            for _, definition in sorted(self._definitions.items(), key=lambda item: item[0])
        )

    def run(self, context: Any) -> list[CheckResult]:
        results: list[CheckResult] = []
        for definition in self.definitions():
            evaluated = definition.evaluator(context)
            for result in evaluated:
                provenance = (result.check_id, result.check_version, result.section)
                expected = (definition.id, definition.version, definition.section)
                if provenance != expected:
                    raise ValueError(
                        f"result provenance {provenance!r} does not match definition {expected!r}"
                    )
            results.extend(evaluated)
        return results
