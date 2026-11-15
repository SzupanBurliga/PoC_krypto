import pytest

from pqcbench.core import ATTACKS, OpCounter, get_attack, get_problem, load_plugins


def test_all_attacks_are_registered():
    load_plugins()
    assert {"lwe-bruteforce", "lwe-primal-lll", "lwe-primal-bkz20"} <= set(ATTACKS)


@pytest.mark.parametrize(
    "attack_name, n",
    [("lwe-bruteforce", 7), ("lwe-primal-lll", 16), ("lwe-primal-bkz20", 16)],
)
def test_attack_recovers_secret(attack_name, n):
    problem = get_problem("lwe")
    instance = problem.generate({"n": n}, seed=11)
    ops = OpCounter()
    solution = get_attack(attack_name).run(instance.public(), ops)
    assert problem.verify(instance, solution)
    assert ops.value > 0


def test_bruteforce_counts_at_most_all_candidates():
    problem = get_problem("lwe")
    instance = problem.generate({"n": 6}, seed=5)
    ops = OpCounter()
    get_attack("lwe-bruteforce").run(instance.public(), ops)
    assert 1 <= ops.value <= 3**6
