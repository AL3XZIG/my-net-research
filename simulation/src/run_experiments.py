"""Run the predefined E1-E5 experiments and write raw CSV results."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from simulation.src.model import Gateway, simulate

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw-data"


def write_rows(filename: str, rows: list[dict[str, object]]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with (RAW_DIR / filename).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_all(trials: int = 10_000, seed: int = 42) -> dict[str, list[dict[str, object]]]:
    rows: dict[str, list[dict[str, object]]] = {f"E{i}": [] for i in range(1, 6)}
    networks = ["A", "B"]

    # E1: number of parallel gateways, each with a distinct operator.
    for count in range(1, 11):
        gateways = [Gateway(f"g{i}", "A", "B", f"operator-{i}") for i in range(count)]
        result = simulate(networks, gateways, trials, 0.1, 0.0, seed + count)
        rows["E1"].append({"gateways": count, **result})

    # E2: a single central gateway versus a pair of alternatives.
    for label, gateways in (
        ("single", [Gateway("g1", "A", "B", "op-1")]),
        ("parallel", [
            Gateway("g1", "A", "B", "op-1"),
            Gateway("g2", "A", "B", "op-2"),
        ]),
    ):
        result = simulate(networks, gateways, trials, 0.1, 0.0, seed + 20)
        rows["E2"].append({"topology": label, **result})

    # E3: same number of gateways in a central bottleneck and a mesh.
    chain = ["A", "B", "C", "D"]
    topologies = {
        "chain": [
            Gateway("g1", "A", "B", "op-1"),
            Gateway("g2", "B", "C", "op-2"),
            Gateway("g3", "C", "D", "op-3"),
        ],
        "mesh_with_alternative": [
            Gateway("g1", "A", "B", "op-1"),
            Gateway("g2", "B", "D", "op-2"),
            Gateway("g3", "A", "C", "op-3"),
            Gateway("g4", "C", "D", "op-4"),
        ],
    }
    for label, gateways in topologies.items():
        result = simulate(chain, gateways, trials, 0.1, 0.0, seed + 30, "A", "D")
        rows["E3"].append({"topology": label, **result})

    # E4: independent gateway failures versus a common operator failure.
    for label, gateways, p_operator in (
        ("independent_operators", [
            Gateway("g1", "A", "B", "op-1"),
            Gateway("g2", "A", "B", "op-2"),
            Gateway("g3", "A", "B", "op-3"),
        ], 0.0),
        ("shared_operator", [
            Gateway("g1", "A", "B", "shared"),
            Gateway("g2", "A", "B", "shared"),
            Gateway("g3", "A", "B", "shared"),
        ], 0.1),
    ):
        result = simulate(networks, gateways, trials, 0.1, p_operator, seed + 40)
        rows["E4"].append({"operator_model": label, **result})

    # E5: vary the fraction of gateways assigned to one common operator.
    for shared_count in range(0, 6):
        gateways = [
            Gateway(f"g{i}", "A", "B", "shared" if i < shared_count else f"op-{i}")
            for i in range(5)
        ]
        result = simulate(networks, gateways, trials, 0.05, 0.1, seed + 50 + shared_count)
        rows["E5"].append({"gateways_on_shared_operator": shared_count, **result})

    for experiment, data in rows.items():
        write_rows(f"{experiment.lower()}.csv", data)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    results = run_all(args.trials, args.seed)
    for name, data in results.items():
        print(f"{name}: {len(data)} scenarios written to {RAW_DIR}")


if __name__ == "__main__":
    main()
