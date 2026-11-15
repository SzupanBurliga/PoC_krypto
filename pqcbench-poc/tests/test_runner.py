import pandas as pd

from pqcbench.core import get_problem
from pqcbench.results import RunWriter, plot, summarize
from pqcbench.runner import expand_grid, run_experiment, run_single


def test_expand_grid():
    assert expand_grid({"n": [6, 8], "q": [97]}) == [{"n": 6, "q": 97}, {"n": 8, "q": 97}]


def test_run_single_reports_metrics():
    instance = get_problem("lwe").generate({"n": 6}, seed=1)
    result = run_single("lwe-bruteforce", instance, timeout=30)
    assert result["status"] == "ok" and result["success"]
    assert result["wall_time_s"] > 0
    assert result["ops"] > 0
    assert result["rss_peak_kb"] > 0


def test_run_single_stops_on_timeout():
    # 3^20 kandydatów nie da się sprawdzić w sekundę
    instance = get_problem("lwe").generate({"n": 20}, seed=1)
    result = run_single("lwe-bruteforce", instance, timeout=1)
    assert result["status"] == "timeout"
    assert not result["success"]


def test_experiment_writes_csv_summary_and_plot(tmp_path):
    runs_csv = tmp_path / "runs.csv"
    writer = RunWriter(runs_csv)
    rows = run_experiment(
        "lwe", ["lwe-bruteforce", "lwe-primal-lll"], {"n": [6, 8]},
        instances=1, repetitions=2, timeout=30, seed=1, on_row=writer.write,
    )
    assert len(rows) == 2 * 1 * 2 * 2

    runs = pd.read_csv(runs_csv)
    assert len(runs) == len(rows)
    assert runs["success"].all()
    # oba ataki dostają te same instancje
    seeds = runs.groupby("attack")["instance_seed"].apply(list)
    assert seeds["lwe-bruteforce"] == seeds["lwe-primal-lll"]

    summary = summarize(runs_csv)
    assert len(summary) == 4
    assert (summary["success_rate"] == 1.0).all()

    plot(summary, tmp_path / "plot.png")
    assert (tmp_path / "plot.png").stat().st_size > 0


def test_experiment_is_reproducible():
    def seeds():
        rows = run_experiment("lwe", ["lwe-primal-lll"], {"n": [6]},
                              instances=2, repetitions=1, timeout=30, seed=42)
        return [(r["instance_seed"], r["ops"]) for r in rows]

    assert seeds() == seeds()
