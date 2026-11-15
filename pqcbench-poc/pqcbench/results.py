"""Zapis wyników do CSV, podsumowanie statystyczne i wykres porównawczy."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

FIELDS = [
    "problem",
    "attack",
    "size",
    "params",
    "instance",
    "instance_seed",
    "repetition",
    "status",
    "success",
    "wall_time_s",
    "cpu_time_s",
    "mem_peak_kb",
    "rss_peak_kb",
    "ops",
    "ops_unit",
    "timeout_s",
    "error",
]


class RunWriter:
    """Dopisuje wiersze do pliku CSV; nagłówek tylko w nowym pliku."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._new = not self.path.exists() or self.path.stat().st_size == 0

    def write(self, row: dict) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            if self._new:
                writer.writeheader()
                self._new = False
            writer.writerow(row)


def summarize(runs_csv: str | Path) -> pd.DataFrame:
    """Jeden wiersz na (problem, atak, rozmiar).

    Skuteczność liczymy po wszystkich uruchomieniach (limit czasu = porażka).
    Czas, pamięć i liczbę operacji liczymy po uruchomieniach, które się zakończyły.
    """
    runs = pd.read_csv(runs_csv)
    done = runs[runs["status"] == "ok"]
    keys = ["problem", "attack", "size"]

    summary = runs.groupby(keys).agg(
        runs=("status", "size"),
        success_rate=("success", "mean"),
        timeouts=("status", lambda s: int((s == "timeout").sum())),
        errors=("status", lambda s: int((s == "error").sum())),
        ops_unit=("ops_unit", "first"),
    )
    stats = done.groupby(keys).agg(
        time_median_s=("wall_time_s", "median"),
        time_mean_s=("wall_time_s", "mean"),
        time_std_s=("wall_time_s", "std"),
        cpu_mean_s=("cpu_time_s", "mean"),
        mem_peak_mean_kb=("mem_peak_kb", "mean"),
        ops_mean=("ops", "mean"),
    )
    columns = [
        "runs",
        "success_rate",
        "timeouts",
        "errors",
        "time_median_s",
        "time_mean_s",
        "time_std_s",
        "cpu_mean_s",
        "mem_peak_mean_kb",
        "ops_mean",
        "ops_unit",
    ]
    return summary.join(stats, how="left")[columns].reset_index()


# Kolory i znaczniki przypisane na stałe do kolejnych serii.
SERIES_STYLE = [("#2a78d6", "o"), ("#eb6834", "s"), ("#1baf7a", "^"), ("#6250d6", "D")]
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"


def plot(summary: pd.DataFrame, path: str | Path) -> None:
    """Dwa panele: mediana czasu (skala log) i skuteczność w funkcji rozmiaru."""
    attacks = sorted(summary["attack"].unique())
    problem = summary["problem"].iloc[0]

    figure, (ax_time, ax_success) = plt.subplots(
        2, 1, figsize=(8, 7), sharex=True, facecolor=SURFACE, gridspec_kw={"height_ratios": [3, 2]}
    )

    for index, attack in enumerate(attacks):
        color, marker = SERIES_STYLE[index % len(SERIES_STYLE)]
        data = summary[summary["attack"] == attack].sort_values("size")
        style = dict(color=color, marker=marker, linewidth=2, markersize=8,
                     markeredgecolor=SURFACE, markeredgewidth=1.5, label=attack)
        timed = data.dropna(subset=["time_median_s"])
        ax_time.plot(timed["size"], timed["time_median_s"], **style)
        ax_success.plot(data["size"], data["success_rate"] * 100, **style)

    ax_time.set_yscale("log")
    ax_time.minorticks_off()
    ax_time.set_ylabel("mediana czasu [s]", color=TEXT_SECONDARY)
    ax_time.set_title(f"Problem {problem.upper()}: czas działania i skuteczność metod",
                      color=TEXT, fontsize=13, fontweight="bold", loc="left", pad=12)
    ax_time.legend(frameon=False, labelcolor=TEXT, loc="lower right")

    ax_success.set_ylabel("skuteczność [%]", color=TEXT_SECONDARY)
    ax_success.set_xlabel("rozmiar instancji (n)", color=TEXT_SECONDARY)
    ax_success.set_ylim(-5, 105)
    ax_success.set_yticks([0, 25, 50, 75, 100])

    for axis in (ax_time, ax_success):
        axis.set_facecolor(SURFACE)
        axis.grid(True, which="major", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
        axis.tick_params(colors=TEXT_SECONDARY, length=0)
        for side in ("top", "right", "left"):
            axis.spines[side].set_visible(False)
        axis.spines["bottom"].set_color(GRID)

    figure.tight_layout()
    figure.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(figure)
