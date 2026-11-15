"""Rdzeń frameworka: typy danych, interfejsy Problem i Attack, rejestr wtyczek.

To jest jedyny plik, od którego zależą wszystkie pozostałe moduły.
Zmiany tutaj wymagają zgody całego zespołu.
"""

from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Instance:
    """Jedna instancja problemu testowego.

    problem   nazwa rodziny problemów, np. "lwe"
    params    parametry instancji (jawne), np. {"n": 10, "m": 20, "q": 97}
    data      dane publiczne, które dostaje atak (np. macierz A i wektor b)
    solution  ukryte rozwiązanie; atak nigdy go nie widzi
    seed      ziarno, z którego instancja została wygenerowana
    """

    problem: str
    params: dict
    data: dict
    solution: Any
    seed: int

    def public(self) -> "Instance":
        """Kopia bez rozwiązania. Tylko taką kopię dostaje atak."""
        return replace(self, solution=None)


class OpCounter:
    """Licznik operacji. Atak sam zgłasza, ile operacji wykonał."""

    def __init__(self) -> None:
        self.value = 0

    def add(self, n: int = 1) -> None:
        self.value += int(n)


class Problem(ABC):
    """Rodzina problemów: generuje instancje i sprawdza rozwiązania."""

    name: str = ""
    #: parametr opisujący rozmiar instancji (oś X na wykresach)
    size_param: str = "n"

    @abstractmethod
    def generate(self, params: dict, seed: int) -> Instance:
        """Tworzy instancję ze znanym rozwiązaniem. To samo ziarno = ta sama instancja."""

    @abstractmethod
    def verify(self, instance: Instance, solution: Any) -> bool:
        """Zwraca True, jeśli `solution` jest poprawnym rozwiązaniem instancji."""

    def shuffle(self, instance: Instance, rng: np.random.Generator) -> Instance:
        """Zwraca równoważną instancję z losowo zmienioną kolejnością danych.

        Domyślnie nic nie zmienia. Rodzina problemów nadpisuje tę metodę,
        jeśli kolejność danych może wpływać na czas działania ataków.
        """
        return instance


class Attack(ABC):
    """Metoda ataku na jedną rodzinę problemów."""

    name: str = ""
    #: nazwa rodziny problemów, którą atakuje ta metoda
    problem: str = ""
    #: co liczy licznik operacji, np. "sprawdzeni kandydaci"
    ops_unit: str = ""

    @abstractmethod
    def run(self, instance: Instance, ops: OpCounter) -> Any | None:
        """Próbuje rozwiązać instancję. Zwraca rozwiązanie albo None."""


# --- rejestr wtyczek -------------------------------------------------------

PROBLEMS: dict[str, Problem] = {}
ATTACKS: dict[str, Attack] = {}
#: moduły, których nie udało się załadować (np. brak opcjonalnej biblioteki)
UNAVAILABLE: dict[str, str] = {}

_loaded = False


def register_problem(cls: type[Problem]) -> type[Problem]:
    """Dekorator: rejestruje rodzinę problemów pod jej nazwą."""
    if not cls.name:
        raise ValueError(f"{cls.__name__}: brak atrybutu name")
    PROBLEMS[cls.name] = cls()
    return cls


def register_attack(cls: type[Attack]) -> type[Attack]:
    """Dekorator: rejestruje metodę ataku pod jej nazwą."""
    if not cls.name or not cls.problem:
        raise ValueError(f"{cls.__name__}: brak atrybutu name lub problem")
    ATTACKS[cls.name] = cls()
    return cls


def load_plugins() -> None:
    """Importuje wszystkie moduły z pqcbench.problems i pqcbench.attacks.

    Moduł, którego import się nie powiódł (np. brak SageMath), nie przerywa
    działania: trafia do UNAVAILABLE razem z komunikatem błędu.
    """
    global _loaded
    if _loaded:
        return
    for package_name in ("pqcbench.problems", "pqcbench.attacks"):
        package = importlib.import_module(package_name)
        for module in pkgutil.iter_modules(package.__path__):
            full_name = f"{package_name}.{module.name}"
            try:
                importlib.import_module(full_name)
            except ImportError as exc:
                UNAVAILABLE[full_name] = str(exc)
    _loaded = True


def get_problem(name: str) -> Problem:
    load_plugins()
    if name not in PROBLEMS:
        raise KeyError(f"Nieznany problem '{name}'. Dostępne: {sorted(PROBLEMS)}")
    return PROBLEMS[name]


def get_attack(name: str) -> Attack:
    load_plugins()
    if name not in ATTACKS:
        raise KeyError(f"Nieznany atak '{name}'. Dostępne: {sorted(ATTACKS)}")
    return ATTACKS[name]
