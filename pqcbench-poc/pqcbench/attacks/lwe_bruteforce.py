"""Atak wyczerpujący na LWE: sprawdza wszystkie sekrety z {-1, 0, 1}^n.

Punkt odniesienia dla pozostałych metod. Złożoność 3^n.
"""

from __future__ import annotations

import numpy as np

from pqcbench.core import Attack, Instance, OpCounter, register_attack
from pqcbench.problems.lwe import centered

CHUNK = 1 << 14  # liczba kandydatów sprawdzanych jednym wywołaniem numpy


@register_attack
class LweBruteForce(Attack):
    name = "lwe-bruteforce"
    problem = "lwe"
    ops_unit = "sprawdzeni kandydaci"

    def run(self, instance: Instance, ops: OpCounter):
        A, b = instance.data["A"], instance.data["b"]
        q, eta = instance.params["q"], instance.params["eta"]
        n = A.shape[1]
        total = 3**n
        powers = 3 ** np.arange(n, dtype=np.int64)

        for start in range(0, total, CHUNK):
            index = np.arange(start, min(start + CHUNK, total), dtype=np.int64)
            # kolejne liczby w systemie trójkowym -> wektory z {-1, 0, 1}^n
            candidates = (index[:, None] // powers[None, :]) % 3 - 1
            residual = centered(b[None, :] - candidates @ A.T, q)
            hits = np.flatnonzero(np.all(np.abs(residual) <= eta, axis=1))
            if hits.size:
                ops.add(int(hits[0]) + 1)
                return candidates[hits[0]]
            ops.add(index.size)
        return None
