import numpy as np

from pqcbench.core import get_problem
from pqcbench.problems.lwe import centered


def make(n=8, seed=7):
    return get_problem("lwe").generate({"n": n}, seed)


def test_same_seed_gives_same_instance():
    a, b = make(seed=3), make(seed=3)
    assert np.array_equal(a.data["A"], b.data["A"])
    assert np.array_equal(a.data["b"], b.data["b"])
    assert np.array_equal(a.solution, b.solution)


def test_different_seed_gives_different_instance():
    assert not np.array_equal(make(seed=3).data["A"], make(seed=4).data["A"])


def test_instance_satisfies_lwe_equation():
    inst = make(n=12)
    A, b, s = inst.data["A"], inst.data["b"], inst.solution
    q, eta = inst.params["q"], inst.params["eta"]
    error = centered(b - A @ s, q)
    assert np.all(np.abs(error) <= eta)
    assert set(np.unique(s)) <= {-1, 0, 1}
    assert A.shape == (inst.params["m"], inst.params["n"])


def test_verify_accepts_only_planted_secret():
    problem = get_problem("lwe")
    inst = make()
    assert problem.verify(inst, inst.solution)
    wrong = inst.solution.copy()
    wrong[0] = 1 if wrong[0] != 1 else 0
    assert not problem.verify(inst, wrong)
    assert not problem.verify(inst, None)
    assert not problem.verify(inst, inst.solution[:-1])


def test_public_copy_hides_solution():
    inst = make()
    assert inst.public().solution is None
    assert inst.solution is not None


def test_shuffle_keeps_instance_valid_and_changes_order():
    problem = get_problem("lwe")
    inst = make(n=12)
    shuffled = problem.shuffle(inst, np.random.default_rng(0))
    A, b, s = shuffled.data["A"], shuffled.data["b"], shuffled.solution
    error = centered(b - A @ s, inst.params["q"])
    assert np.all(np.abs(error) <= inst.params["eta"])
    assert not np.array_equal(A, inst.data["A"])
    assert sorted(s.tolist()) == sorted(inst.solution.tolist())
