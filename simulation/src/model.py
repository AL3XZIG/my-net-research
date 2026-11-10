"""Monte Carlo model of connectivity between independent networks.

Networks are vertices; gateways are edges. Gateway failures are independent
unless gateways share an operator that experiences a common failure.
This is an abstract graph model, not a protocol-level network simulator.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from random import Random
from typing import Iterable


@dataclass(frozen=True)
class Gateway:
    """A bidirectional gateway between two network identifiers."""

    gateway_id: str
    source: str
    target: str
    operator: str


@dataclass(frozen=True)
class TrialResult:
    """Connectivity outcome for one Monte Carlo trial."""

    connected: bool
    active_gateways: int
    failed_operators: tuple[str, ...]


def is_connected(
    networks: Iterable[str],
    gateways: Iterable[Gateway],
    failed_gateway_ids: set[str] | None = None,
    source: str | None = None,
    target: str | None = None,
) -> bool:
    """Return whether source and target are connected by active gateways.

    If source/target are omitted, the first and last network identifiers are
    used. An empty network collection is not connected.
    """
    network_list = list(networks)
    if not network_list:
        return False
    start = source if source is not None else network_list[0]
    finish = target if target is not None else network_list[-1]
    if start not in network_list or finish not in network_list:
        raise ValueError("source and target must be present in networks")
    if start == finish:
        return True

    failed = failed_gateway_ids or set()
    adjacency: dict[str, list[str]] = {network: [] for network in network_list}
    for gateway in gateways:
        if gateway.gateway_id in failed:
            continue
        if gateway.source not in adjacency or gateway.target not in adjacency:
            raise ValueError(f"Gateway {gateway.gateway_id!r} references an unknown network")
        adjacency[gateway.source].append(gateway.target)
        adjacency[gateway.target].append(gateway.source)

    queue = deque([start])
    visited = {start}
    while queue:
        current = queue.popleft()
        for neighbour in adjacency[current]:
            if neighbour == finish:
                return True
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)
    return False


def run_trial(
    networks: Iterable[str],
    gateways: Iterable[Gateway],
    gateway_failure_probability: float,
    operator_failure_probability: float,
    rng: Random,
    source: str | None = None,
    target: str | None = None,
) -> TrialResult:
    """Run one trial with independent gateway and shared operator failures."""
    _validate_probability(gateway_failure_probability, "gateway_failure_probability")
    _validate_probability(operator_failure_probability, "operator_failure_probability")
    network_list = list(networks)
    gateway_list = list(gateways)

    operators = sorted({gateway.operator for gateway in gateway_list})
    failed_operators = {
        operator for operator in operators
        if rng.random() < operator_failure_probability
    }
    failed_gateway_ids = {
        gateway.gateway_id for gateway in gateway_list
        if gateway.operator in failed_operators
        or rng.random() < gateway_failure_probability
    }
    connected = is_connected(
        network_list, gateway_list, failed_gateway_ids, source, target
    )
    return TrialResult(
        connected=connected,
        active_gateways=len(gateway_list) - len(failed_gateway_ids),
        failed_operators=tuple(sorted(failed_operators)),
    )


def simulate(
    networks: Iterable[str],
    gateways: Iterable[Gateway],
    trials: int = 10_000,
    gateway_failure_probability: float = 0.1,
    operator_failure_probability: float = 0.0,
    seed: int = 42,
    source: str | None = None,
    target: str | None = None,
) -> dict[str, float | int]:
    """Estimate connectivity probability and average active gateway count."""
    if trials < 1:
        raise ValueError("trials must be at least 1")
    network_list = list(networks)
    gateway_list = list(gateways)
    rng = Random(seed)

    connected_count = 0
    active_total = 0
    for _ in range(trials):
        outcome = run_trial(
            network_list,
            gateway_list,
            gateway_failure_probability,
            operator_failure_probability,
            rng,
            source,
            target,
        )
        connected_count += int(outcome.connected)
        active_total += outcome.active_gateways

    return {
        "trials": trials,
        "connected_trials": connected_count,
        "availability": connected_count / trials,
        "mean_active_gateways": active_total / trials,
        "seed": seed,
    }


def _validate_probability(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
