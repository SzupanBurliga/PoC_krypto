# README — PoC pqcbench

## Co to jest
PoC do benchmarkowania ataków na LWE (post-kwantowa krypto). Ma 3 metody,
testy i wykresy.

## Jak odpalić

1. Klonujesz repo, wchodzisz do folderu.
2. **Windows?** Musisz mieć WSL2 (Ubuntu) — fpylll nie działa na czystym
   Windowsie. `wsl --install` w PowerShellu jako admin, restart, dalej
   pracujesz w WSL.
   Mac/Linux — bez problemu, lecisz dalej.
3. W terminalu (WSL/Linux/Mac):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Sprawdzenie, że działa:

```bash
python -m pytest -v
```

Ma wyjść: `16 passed`.

5. Przykład:

```bash
python -m pqcbench run --problem lwe --grid n=6,8,10,12,14 --out results
```

Wyniki w `results/` (`runs.csv`, `summary.csv`, `plot.png`).

## Każda następna sesja

```bash
cd NAZWA_REPO
source .venv/bin/activate
```

## Coś nie działa?
Pisz na kanale — zazwyczaj brakujący pakiet systemowy pod fpylll.
