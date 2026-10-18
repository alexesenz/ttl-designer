import pytest

from ttl_designer.logic.parser import parse_equations, parse_expression
from ttl_designer.logic.truthtable import input_vectors, minterms, ones, truth_table


@pytest.mark.parametrize("n", range(0, 7))
def test_input_vectors_match_naive(n):
    vectors, mask = input_vectors(n)
    assert mask == (1 << (1 << n)) - 1
    for i, vec in enumerate(vectors):
        for r in range(1 << n):
            assert (vec >> r) & 1 == (r >> (n - 1 - i)) & 1


def test_ones():
    assert ones(0) == []
    assert ones(0b1011) == [0, 1, 3]


def test_minterms_msb_is_first_variable():
    assert minterms(parse_expression("A"), ["A", "B"]) == [2, 3]
    assert minterms(parse_expression("B"), ["A", "B"]) == [1, 3]


def test_minterms_rejects_undeclared():
    with pytest.raises(ValueError):
        minterms(parse_expression("A B"), ["A"])


def test_full_adder_table():
    t = truth_table(parse_equations("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)"))
    assert t.inputs == ["A", "B", "Ci"]
    for ins, (s, co) in t.rows():
        total = sum(ins)
        assert s == total % 2 and co == total // 2


def test_output_used_as_input_rejected():
    with pytest.raises(ValueError):
        truth_table(parse_equations("X = A B; Y = X + C"))


def test_sixteen_inputs():
    names = [f"I{i}" for i in range(16)]
    t = truth_table(parse_equations("Y = " + " ".join(names)))
    assert t.minterms("Y") == [(1 << 16) - 1]
