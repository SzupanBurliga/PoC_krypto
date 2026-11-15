"""Pomiar metryk jednego uruchomienia ataku.

Każdy atak działa w osobnym procesie. Dzięki temu:
- pamięć mierzymy dla całego procesu (także dla bibliotek w C/C++),
- pomiary nie wpływają na siebie nawzajem,
- atak, który przekroczy limit czasu, można po prostu zakończyć.

Dwie metryki pamięci:
- rss_peak_kb  szczytowe zużycie pamięci całego procesu (interpreter + biblioteki + atak),
- mem_peak_kb  o ile atak podniósł zużycie pamięci ponad stan sprzed uruchomienia.
"""

from __future__ import annotations

import resource
import sys
import time
import traceback


def peak_rss_kb() -> int:
    """Szczytowe zużycie pamięci bieżącego procesu w kB.

    Na Linuksie czytamy VmHWM z /proc/self/status. Licznik ru_maxrss
    obejmuje też pamięć procesu sprzed exec(), więc zawyżałby wynik.
    """
    try:
        with open("/proc/self/status") as handle:
            for line in handle:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1])
    except OSError:
        pass
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux podaje kB, macOS bajty
    return int(value // 1024) if sys.platform == "darwin" else int(value)


def current_rss_kb() -> int:
    """Bieżące zużycie pamięci w kB (Linux); na innych systemach wartość szczytowa."""
    try:
        with open("/proc/self/statm") as handle:
            pages = int(handle.read().split()[1])
        return pages * resource.getpagesize() // 1024
    except OSError:
        return peak_rss_kb()


def reset_peak_rss() -> bool:
    """Zeruje licznik szczytowego zużycia pamięci (tylko Linux).

    Bez tego szczyt z fazy importów bibliotek zasłaniałby zużycie małych ataków.
    """
    try:
        with open("/proc/self/clear_refs", "w") as handle:
            handle.write("5")
        return True
    except OSError:
        return False


def worker(attack_name: str, instance, connection) -> None:
    """Kod wykonywany w procesie potomnym: uruchamia atak i odsyła metryki."""
    try:
        from pqcbench.core import OpCounter, get_attack

        attack = get_attack(attack_name)
        ops = OpCounter()

        process_peak = peak_rss_kb()
        reset_peak_rss()
        rss_before = current_rss_kb()
        wall_start = time.perf_counter()
        cpu_start = time.process_time()

        solution = attack.run(instance, ops)

        cpu_time = time.process_time() - cpu_start
        wall_time = time.perf_counter() - wall_start
        rss_after = peak_rss_kb()

        connection.send(
            {
                "status": "ok",
                "solution": solution,
                "wall_time_s": wall_time,
                "cpu_time_s": cpu_time,
                "ops": ops.value,
                "rss_peak_kb": max(process_peak, rss_after),
                "mem_peak_kb": max(0, rss_after - rss_before),
                "error": "",
            }
        )
    except Exception:  # błąd ataku nie może przerwać całego eksperymentu
        connection.send({"status": "error", "error": traceback.format_exc(limit=3)})
    finally:
        connection.close()
