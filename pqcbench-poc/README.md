# pqcbench: benchmark metod kryptoanalizy postkwantowej (PoC)

Minimalna, działająca wersja frameworka. Pokazuje cały przepływ na jednym
problemie (LWE) i trzech metodach:

| Metoda | Co robi | Biblioteka |
| --- | --- | --- |
| `lwe-bruteforce` | sprawdza wszystkie sekrety z {-1, 0, 1}^n | numpy (kod własny, punkt odniesienia) |
| `lwe-primal-lll` | atak pierwotny: osadzenie Kannana + redukcja LLL | fpylll |
| `lwe-primal-bkz20` | atak pierwotny: osadzenie Kannana + BKZ, blok 20 | fpylll |

## Wymagania

- Linux, macOS albo Windows z WSL2 (fpylll nie ma wersji na czysty Windows)
- Python 3.10 lub nowszy

## Instalacja

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Jak przetestować

### 1. Testy automatyczne (ok. 5 sekund)

```bash
python -m pytest -v
```

Oczekiwany wynik: `16 passed`. Testy sprawdzają generator instancji,
weryfikację rozwiązań, każdy z trzech ataków, limit czasu, zapis CSV,
podsumowanie, wykres i powtarzalność wyników.

### 2. Lista dostępnych problemów i ataków

```bash
python -m pqcbench list
```

### 3. Szybki eksperyment (ok. 30 sekund)

Wszystkie trzy metody na małych instancjach:

```bash
python -m pqcbench run --problem lwe --grid n=6,8,10,12,14 --out results
```

### 4. Eksperyment na większych instancjach (ok. 2 minuty)

Tylko metody kratowe; wyniki dopisują się do tego samego pliku:

```bash
python -m pqcbench run --problem lwe --grid n=20,30,40,50,60 \
    --attacks lwe-primal-lll lwe-primal-bkz20 --timeout 60 --out results
```

### 5. Wyniki

W katalogu `results/` powstają trzy pliki:

- `runs.csv`: jeden wiersz na każde uruchomienie ataku
- `summary.csv`: statystyki dla każdej pary (atak, rozmiar)
- `plot.png`: mediana czasu i skuteczność w funkcji `n`

Podsumowanie i wykres można odtworzyć z istniejących danych:

```bash
python -m pqcbench report results/runs.csv
```

Gotowe wyniki z uruchomienia referencyjnego są w `example_results/`.

### Czego się spodziewać

- Czas ataku wyczerpującego rośnie około 9 razy przy każdym zwiększeniu `n` o 2.
- LLL odzyskuje sekret do `n = 30`, przy `n = 40` tylko czasami, od `n = 50` wcale.
- BKZ z blokiem 20 działa do `n = 40-50` i przestaje przy `n = 60`.

## Opcje polecenia `run`

| Opcja | Znaczenie | Domyślnie |
| --- | --- | --- |
| `--problem` | rodzina problemów | wymagane |
| `--grid` | parametry instancji, np. `n=6,8,10 q=97 eta=2` | wymagane |
| `--attacks` | lista metod | wszystkie dla problemu |
| `--instances` | liczba losowych instancji na zestaw parametrów | 2 |
| `--repetitions` | liczba powtórzeń na instancję (każde z inną kolejnością danych) | 5 |
| `--timeout` | limit czasu jednego uruchomienia w sekundach | 30 |
| `--seed` | ziarno eksperymentu | 1 |
| `--out` | katalog na wyniki | `results` |

Parametry LWE: `n` (wymiar sekretu), `m` (liczba próbek, domyślnie `2n`),
`q` (moduł, domyślnie 97), `eta` (ograniczenie błędu, domyślnie 2).

## Kolumny w `runs.csv`

| Kolumna | Znaczenie |
| --- | --- |
| `problem`, `attack`, `size`, `params` | co i na czym uruchomiono |
| `instance`, `instance_seed`, `repetition` | która instancja i które powtórzenie |
| `status` | `ok`, `timeout` albo `error` |
| `success` | czy atak zwrócił poprawne rozwiązanie |
| `wall_time_s`, `cpu_time_s` | czas zegarowy i czas procesora samego ataku |
| `mem_peak_kb` | o ile atak podniósł zużycie pamięci procesu |
| `rss_peak_kb` | szczytowe zużycie pamięci całego procesu |
| `ops`, `ops_unit` | liczba operacji i co dokładnie jest liczone |

## Jak dodać nową metodę

Wystarczy jeden plik w `pqcbench/attacks/`. Przykład: BKZ z blokiem 30.

```python
# pqcbench/attacks/lwe_primal_bkz30.py
from pqcbench.attacks.lwe_primal import _LwePrimal
from pqcbench.core import register_attack


@register_attack
class LwePrimalBKZ30(_LwePrimal):
    name = "lwe-primal-bkz30"
    ops_unit = "węzły enumeracji w BKZ"
    block_size = 30
```

Metoda pojawi się w `python -m pqcbench list` bez zmian w innych plikach.
Zupełnie nowa metoda dziedziczy po `Attack` i implementuje `run(instance, ops)`.

## Jak dodać nową rodzinę problemów

Jeden plik w `pqcbench/problems/` z klasą dziedziczącą po `Problem`
(`generate`, `verify`, opcjonalnie `shuffle`) i dekoratorem `@register_problem`.
Wzorzec: `pqcbench/problems/lwe.py`.

## Struktura

```
pqcbench/
  core.py        interfejsy Problem i Attack, typ Instance, rejestr wtyczek
  runner.py      plan eksperymentu, osobny proces na atak, limit czasu
  metrics.py     pomiar czasu, pamięci i liczby operacji
  results.py     zapis CSV, podsumowanie, wykres
  cli.py         polecenia list / run / report
  problems/      lwe.py
  attacks/       lwe_bruteforce.py, lwe_primal.py
tests/           testy pytest
```

## Ograniczenia PoC

- Dokładny pomiar `mem_peak_kb` działa na Linuksie (także WSL2). Na macOS
  wartość może być zawyżona o stałą, bo systemu nie da się poprosić o
  wyzerowanie licznika szczytowego zużycia pamięci.
- Liczba operacji ma inną jednostkę dla każdej metody (kolumna `ops_unit`),
  więc nie należy jej porównywać między metodami.
- Konfiguracja tylko z wiersza poleceń; plik konfiguracyjny dojdzie później.
