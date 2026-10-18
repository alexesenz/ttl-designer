import random
from itertools import combinations

import pytest

from ttl_designer.logic.qm import Implicant, merge_pair, minimize


def covered(cover, n):
    return {m for imp in cover for m in imp.minterms(n)}


def check_cover(n, ms, dcs, res):
    cov = covered(res.cover, n)
    assert set(ms) <= cov
    assert cov <= set(ms) | set(dcs)
    assert set(res.cover) <= set(res.trace.prime_implicants)


def test_merge_pair():
    assert merge_pair(Implicant(0b000, 0), Implicant(0b001, 0)) == Implicant(0b000, 0b001)
    assert merge_pair(Implicant(0b000, 0), Implicant(0b011, 0)) is None
    assert merge_pair(Implicant(0b000, 0b001), Implicant(0b100, 0)) is None


def test_pattern_and_expr():
    imp = Implicant(0b100, 0b001)
    assert imp.pattern(3) == "10-"
    assert str(imp.to_expr(["A", "B", "C"])) == "A·B'"


def test_empty_and_full():
    assert minimize(3, []).cover == []
    assert str(minimize(2, [0, 1, 2, 3]).to_expr(["A", "B"])) == "1"


def test_cyclic_cover_uses_petrick():
    # Σm(0,1,2,5,6,7): sin esenciales, dos soluciones mínimas de 3 términos
    res = minimize(3, [0, 1, 2, 5, 6, 7])
    assert res.trace.essential == []
    assert res.trace.method == "petrick"
    assert res.trace.petrick_alternatives >= 2
    assert len(res.cover) == 3
    check_cover(3, [0, 1, 2, 5, 6, 7], [], res)


def test_textbook_with_dont_cares():
    # Σm(4,8,10,11,12,15) + d(9,14) → A B' + A C + B C' D'
    ms, dcs = [4, 8, 10, 11, 12, 15], [9, 14]
    res = minimize(4, ms, dcs)
    check_cover(4, ms, dcs, res)
    assert len(res.cover) == 3
    assert sum(p.literal_count(4) for p in res.cover) == 7


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        minimize(2, [4])
    with pytest.raises(ValueError):
        minimize(2, [1], [1])


def brute_force_min_terms(n, ms, primes):
    for k in range(1, len(primes) + 1):
        for combo in combinations(primes, k):
            if set(ms) <= covered(combo, n):
                return k
    return 0


@pytest.mark.parametrize("n", [2, 3, 4])
def test_random_functions_are_minimal(n):
    rng = random.Random(n)
    for _ in range(150):
        rows = list(range(1 << n))
        ms = [r for r in rows if rng.random() < 0.45]
        dcs = [r for r in rows if r not in ms and rng.random() < 0.15]
        res = minimize(n, ms, dcs)
        check_cover(n, ms, dcs, res)
        if ms:
            assert len(res.cover) == brute_force_min_terms(n, ms, res.trace.prime_implicants)


def test_trace_records_iterations():
    res = minimize(3, [0, 1, 2, 3])
    t = res.trace
    assert len(t.columns) == 3  # minterms, pares, cuádruple
    assert t.prime_implicants == [Implicant(0, 0b011)]
    assert any(it == 1 for it, *_ in t.merges)


def test_dense_function_beyond_cube_limit_is_rejected_quickly():
    import time

    from ttl_designer.logic.qm import TooLargeError

    # A'·B con 16 variables: 2^14 mintérminos contiguos, hasta 3^14 cubos
    n = 16
    ms = [m for m in range(1 << n) if (m >> 15) & 1 == 0 and (m >> 14) & 1 == 1]
    t = time.perf_counter()
    with pytest.raises(TooLargeError):
        minimize(n, ms)
    assert time.perf_counter() - t < 30
