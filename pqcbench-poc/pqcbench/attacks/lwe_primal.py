"""Atak pierwotny na LWE: redukcja do najkrótszego wektora w kracie.

Budujemy kratę (osadzenie Kannana), w której wektor (s, -e, -1) jest
wyjątkowo krótki, i szukamy go redukcją bazy z biblioteki fpylll:
samym LLL albo LLL + BKZ z zadanym rozmiarem bloku.
"""

from __future__ import annotations

import numpy as np
from fpylll import BKZ, GSO, LLL, IntegerMatrix
from fpylll.algorithms.bkz import BKZReduction

from pqcbench.core import Attack, Instance, OpCounter, register_attack


def kannan_basis(A: np.ndarray, b: np.ndarray, q: int) -> IntegerMatrix:
    """Baza kraty wymiaru n + m + 1.

    Wiersze:  [ 0    | q*I_m | 0 ]
              [ I_n  | A^T   | 0 ]
              [ 0    | b     | 1 ]
    Kombinacja s*(wiersze środkowe) - (ostatni wiersz) + wielokrotności q
    daje wektor (s, A*s - b mod q, -1) = (s, -e, -1).
    """
    m, n = A.shape
    d = n + m + 1
    rows = np.zeros((d, d), dtype=np.int64)
    rows[:m, n : n + m] = q * np.eye(m, dtype=np.int64)
    rows[m : m + n, :n] = np.eye(n, dtype=np.int64)
    rows[m : m + n, n : n + m] = A.T
    rows[d - 1, n : n + m] = b
    rows[d - 1, d - 1] = 1
    return IntegerMatrix.from_matrix(rows.tolist())


def extract_secret(basis: IntegerMatrix, n: int, eta: int):
    """Szuka w zredukowanej bazie wektora postaci +-(s, -e, -1)."""
    d = basis.nrows
    for i in range(d):
        row = [basis[i, j] for j in range(d)]
        if abs(row[-1]) != 1:
            continue
        if any(abs(x) > 1 for x in row[:n]) or any(abs(x) > eta for x in row[n:-1]):
            continue
        sign = -row[-1]
        return np.array([sign * x for x in row[:n]], dtype=np.int64)
    return None


class _LwePrimal(Attack):
    problem = "lwe"
    #: rozmiar bloku BKZ; None oznacza sam LLL
    block_size: int | None = None

    def run(self, instance: Instance, ops: OpCounter):
        A, b = instance.data["A"], instance.data["b"]
        q, eta = instance.params["q"], instance.params["eta"]
        basis = kannan_basis(A, b, q)

        gso = GSO.Mat(basis)
        gso.update_gso()
        lll = LLL.Reduction(gso)
        lll()

        if self.block_size is None:
            ops.add(lll.nswaps)
        else:
            bkz = BKZReduction(basis)
            params = BKZ.Param(block_size=self.block_size, max_loops=8, flags=BKZ.MAX_LOOPS)
            bkz(params, tracer=True)
            ops.add(int(float(bkz.trace.sum("#enum"))))

        return extract_secret(basis, A.shape[1], eta)


@register_attack
class LwePrimalLLL(_LwePrimal):
    name = "lwe-primal-lll"
    ops_unit = "zamiany wektorów w LLL"
    block_size = None


@register_attack
class LwePrimalBKZ20(_LwePrimal):
    name = "lwe-primal-bkz20"
    ops_unit = "węzły enumeracji w BKZ"
    block_size = 20
