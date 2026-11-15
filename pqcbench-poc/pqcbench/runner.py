"""Runner: uruchamia ataki na instancjach i zbiera wyniki.

Plan eksperymentu:
  dla każdego zestawu parametrów (np. kolejne n)
    dla każdej instancji (osobne ziarno)
      dla każdego powtórzenia: losowa zmiana kolejności danych
        dla każdego ataku: uruchomienie w osobnym procesie z limitem czasu
"""

from __future__ import annotations

import itertools
import json
import multiprocessing
from typing import Callable, Iterable

import numpy as np

from pqcbench.core import Instance, get_attack, get_problem
from pqcbench.metrics import worker

_SPAWN = multiprocessing.get_context("spawn")

EMPTY_METRICS = {
    "wall_time_s": None,
    "cpu_time_s": None,
    "ops": None,
    "rss_peak_kb": None,
    "mem_peak_kb": None,
    "error": "",
}


def run_single(attack_name: str, instance: Instance, timeout: float) -> dict:
    """Uruchamia jeden atak na jednej instancji i zwraca metryki.

    Atak dostaje instancję bez rozwiązania. Wynik sprawdza proces nadrzędny.
    Pole status: "ok" (atak się zakończył), "timeout" albo "error".
    """
    problem = get_problem(instance.problem)
    attack = get_attack(attack_name)
    if attack.problem != instance.problem:
        raise ValueError(f"Atak '{attack_name}' nie dotyczy problemu '{instance.problem}'")

    receiver, sender = _SPAWN.Pipe(duplex=False)
    process = _SPAWN.Process(target=worker, args=(attack_name, instance.public(), sender))
    process.start()
    sender.close()

    result = dict(EMPTY_METRICS)
    try:
        if receiver.poll(timeout):
            result.update(receiver.recv())
        else:
            result["status"] = "timeout"
    except EOFError:
        result.update(status="error", error="proces ataku zakończył się bez wyniku")
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
        receiver.close()

    solution = result.pop("solution", None)
    result["success"] = bool(result["status"] == "ok" and problem.verify(instance, solution))
    return result


def expand_grid(grid: dict[str, list]) -> list[dict]:
    """{"n": [8, 10], "q": [97]} -> [{"n": 8, "q": 97}, {"n": 10, "q": 97}]"""
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def run_experiment(
    problem_name: str,
    attack_names: Iterable[str],
    grid: dict[str, list],
    instances: int = 2,
    repetitions: int = 5,
    timeout: float = 30.0,
    seed: int = 1,
    on_row: Callable[[dict], None] | None = None,
) -> list[dict]:
    """Uruchamia pełny eksperyment i zwraca listę wierszy (jeden na uruchomienie).

    `on_row` jest wywoływane po każdym uruchomieniu, co pozwala zapisywać
    wyniki na bieżąco i nie tracić ich przy przerwaniu eksperymentu.
    """
    problem = get_problem(problem_name)
    attack_names = list(attack_names)
    rows: list[dict] = []

    for param_index, params in enumerate(expand_grid(grid)):
        for instance_index in range(instances):
            # ziarno zależy tylko od (seed, parametry, numer instancji),
            # więc każdy atak dostaje dokładnie te same instancje
            sequence = np.random.SeedSequence(entropy=seed, spawn_key=(param_index, instance_index))
            instance_seed = int(sequence.generate_state(1)[0])
            base = problem.generate(params, instance_seed)

            for repetition in range(repetitions):
                shuffle_rng = np.random.default_rng([instance_seed, repetition])
                instance = problem.shuffle(base, shuffle_rng)

                for attack_name in attack_names:
                    metrics = run_single(attack_name, instance, timeout)
                    row = {
                        "problem": problem_name,
                        "attack": attack_name,
                        "size": base.params[problem.size_param],
                        "params": json.dumps(base.params, sort_keys=True),
                        "instance": instance_index,
                        "instance_seed": instance_seed,
                        "repetition": repetition,
                        "ops_unit": get_attack(attack_name).ops_unit,
                        "timeout_s": timeout,
                        **metrics,
                    }
                    rows.append(row)
                    if on_row:
                        on_row(row)
    return rows
