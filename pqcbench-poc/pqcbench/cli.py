"""Interfejs wiersza poleceń.

  python -m pqcbench list
  python -m pqcbench run --problem lwe --grid n=6,8,10 --attacks lwe-bruteforce
  python -m pqcbench report results/runs.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pqcbench import core
from pqcbench.results import RunWriter, plot, summarize
from pqcbench.runner import run_experiment


def parse_grid(items: list[str]) -> dict[str, list[int]]:
    """["n=6,8,10", "q=97"] -> {"n": [6, 8, 10], "q": [97]}"""
    grid: dict[str, list[int]] = {}
    for item in items:
        key, _, values = item.partition("=")
        if not key or not values:
            raise SystemExit(f"Niepoprawny parametr '{item}'. Oczekiwany format: n=6,8,10")
        grid[key.strip()] = [int(v) for v in values.split(",")]
    return grid


def cmd_list(_args) -> int:
    core.load_plugins()
    print("Problemy:")
    for name in sorted(core.PROBLEMS):
        print(f"  {name}")
    print("Ataki:")
    for name, attack in sorted(core.ATTACKS.items()):
        print(f"  {name:<20} problem: {attack.problem:<6} licznik: {attack.ops_unit}")
    for module, reason in core.UNAVAILABLE.items():
        print(f"Niedostępny moduł {module}: {reason}")
    return 0


def report(runs_csv: Path) -> None:
    summary = summarize(runs_csv)
    summary_csv = runs_csv.with_name("summary.csv")
    figure = runs_csv.with_name("plot.png")
    summary.to_csv(summary_csv, index=False)
    plot(summary, figure)

    shown = summary[["attack", "size", "runs", "success_rate", "timeouts",
                     "time_median_s", "mem_peak_mean_kb", "ops_mean"]]
    print(shown.to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    print(f"\nPodsumowanie: {summary_csv}\nWykres:       {figure}")


def cmd_run(args) -> int:
    core.load_plugins()
    attacks = args.attacks or sorted(
        name for name, attack in core.ATTACKS.items() if attack.problem == args.problem
    )
    runs_csv = Path(args.out) / "runs.csv"
    writer = RunWriter(runs_csv)

    def on_row(row: dict) -> None:
        writer.write(row)
        time = "-" if row["wall_time_s"] is None else f"{row['wall_time_s']:.3f} s"
        outcome = "sukces" if row["success"] else row["status"] if row["status"] != "ok" else "porażka"
        print(f"{row['attack']:<18} n={row['size']:<4} inst={row['instance']} "
              f"powt={row['repetition']}  {outcome:<8} {time}", flush=True)

    run_experiment(
        problem_name=args.problem,
        attack_names=attacks,
        grid=parse_grid(args.grid),
        instances=args.instances,
        repetitions=args.repetitions,
        timeout=args.timeout,
        seed=args.seed,
        on_row=on_row,
    )
    print()
    report(runs_csv)
    return 0


def cmd_report(args) -> int:
    report(Path(args.runs_csv))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pqcbench", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="pokaż dostępne problemy i ataki").set_defaults(func=cmd_list)

    run = commands.add_parser("run", help="uruchom eksperyment")
    run.add_argument("--problem", required=True)
    run.add_argument("--attacks", nargs="+", help="domyślnie wszystkie ataki dla problemu")
    run.add_argument("--grid", nargs="+", required=True, metavar="PARAM=V1,V2",
                     help="parametry instancji, np. n=6,8,10 q=97")
    run.add_argument("--instances", type=int, default=2, help="liczba instancji na zestaw parametrów")
    run.add_argument("--repetitions", type=int, default=5, help="liczba powtórzeń na instancję")
    run.add_argument("--timeout", type=float, default=30.0, help="limit czasu jednego uruchomienia [s]")
    run.add_argument("--seed", type=int, default=1)
    run.add_argument("--out", default="results", help="katalog na wyniki (runs.csv jest dopisywany)")
    run.set_defaults(func=cmd_run)

    rep = commands.add_parser("report", help="podsumowanie i wykres z istniejącego runs.csv")
    rep.add_argument("runs_csv")
    rep.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)
