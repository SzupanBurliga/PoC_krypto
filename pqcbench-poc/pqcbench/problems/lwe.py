"""Problem LWE (Learning With Errors) z małym sekretem.

Dane publiczne: macierz A (m x n) i wektor b = A*s + e mod q.
Szukane: sekret s. Sekret ma współrzędne z {-1, 0, 1}, błąd e ma rozkład
dwumianowy scentrowany (jak w ML-KEM), więc |e_i| <= eta.
"""

from __future__ import annotations

import numpy as np

from pqcbench.core import Instance, Problem, register_problem


def centered(x: np.ndarray, q: int) -> np.ndarray:
    """Reprezentant modulo q z przedziału (-q/2, q/2]."""
    x = np.mod(x, q)
    return np.where(x > q // 2, x - q, x)


@register_problem
class LWE(Problem):
    name = "lwe"
    size_param = "n"

    #: wartości domyślne; q jest celowo małe, żeby ataki kratowe
    #: przestawały działać już przy kilkudziesięciu wymiarach
    defaults = {"q": 97, "eta": 2}

    def generate(self, params: dict, seed: int) -> Instance:
        p = {**self.defaults, **params}
        n = int(p["n"])
        m = int(p.get("m", 2 * n))
        q = int(p["q"])
        eta = int(p["eta"])
        rng = np.random.default_rng(seed)

        A = rng.integers(0, q, size=(m, n), dtype=np.int64)
        s = rng.integers(-1, 2, size=n, dtype=np.int64)
        e = rng.binomial(eta, 0.5, size=m) - rng.binomial(eta, 0.5, size=m)
        b = np.mod(A @ s + e, q)

        return Instance(
            problem=self.name,
            params={"n": n, "m": m, "q": q, "eta": eta},
            data={"A": A, "b": b},
            solution=s,
            seed=int(seed),
        )

    def verify(self, instance: Instance, solution) -> bool:
        if solution is None:
            return False
        candidate = np.asarray(solution)
        expected = np.asarray(instance.solution)
        return candidate.shape == expected.shape and bool(np.array_equal(candidate, expected))

    def shuffle(self, instance: Instance, rng: np.random.Generator) -> Instance:
        """Losowo zmienia kolejność próbek (wiersze) i zmiennych (kolumny).

        Kolejność współrzędnych sekretu zmienia się razem z kolumnami,
        więc instancja pozostaje poprawna i równie trudna.
        """
        A, b = instance.data["A"], instance.data["b"]
        rows = rng.permutation(A.shape[0])
        cols = rng.permutation(A.shape[1])
        return Instance(
            problem=instance.problem,
            params=dict(instance.params),
            data={"A": A[rows][:, cols], "b": b[rows]},
            solution=np.asarray(instance.solution)[cols],
            seed=instance.seed,
        )
