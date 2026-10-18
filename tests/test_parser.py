import pytest

from ttl_designer.logic.ast import And, Const, Not, Or, Var, Xor
from ttl_designer.logic.parser import ParseError, parse_equations, parse_expression

A, B, C = Var("A"), Var("B"), Var("C")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("A", A),
        ("A·B", And((A, B))),
        ("A*B", And((A, B))),
        ("A & B", And((A, B))),
        ("A B", And((A, B))),
        ("A + B", Or((A, B))),
        ("A | B", Or((A, B))),
        ("A ^ B", Xor((A, B))),
        ("A'", Not(A)),
        ("!A", Not(A)),
        ("~A", Not(A)),
        ("A''", Not(Not(A))),
        ("(A + B)'", Not(Or((A, B)))),
        ("1", Const(True)),
        ("A·0", And((A, Const(False)))),
        ("A B C", And((A, B, C))),
        ("A + B + C", Or((A, B, C))),
    ],
)
def test_basic(text, expected):
    assert parse_expression(text) == expected


def test_precedence_not_and_xor_or():
    # A + B ^ C D'  ==  A + (B ^ (C · D'))
    e = parse_expression("A + B ^ C D'")
    assert e == Or((A, Xor((B, And((C, Not(Var("D"))))))))


def test_implicit_and_with_parentheses():
    e = parse_expression("(A + B)(A + C)")
    assert e == And((Or((A, B)), Or((A, C))))
    assert parse_expression("A(B + C)") == And((A, Or((B, C))))


def test_multichar_identifiers():
    assert parse_expression("AB + sel_1") == Or((Var("AB"), Var("sel_1")))


def test_prime_binds_tighter_than_not():
    assert parse_expression("!A'") == Not(Not(A))


def test_equations_separators():
    eqs = parse_equations("S = A ^ B\nCo = A B; Z = 0\n")
    assert [n for n, _ in eqs] == ["S", "Co", "Z"]


@pytest.mark.parametrize(
    "text, pos",
    [("A +", 3), ("A + (B", 6), ("A $ B", 2), ("(A))", 3)],
)
def test_errors_report_position(text, pos):
    with pytest.raises(ParseError) as exc:
        parse_expression(text)
    assert exc.value.pos == pos


def test_duplicate_outputs_rejected():
    with pytest.raises(ParseError):
        parse_equations("Y = A; Y = B")


def test_equation_requires_name():
    with pytest.raises(ParseError):
        parse_equations("A + B")


def test_roundtrip_through_str(rng):
    from tests.conftest import random_expr
    from ttl_designer.logic.truthtable import minterms

    vs = ["A", "B", "C", "D"]
    for _ in range(200):
        e = random_expr(rng, vs)
        again = parse_expression(e.to_str())
        assert minterms(again, vs) == minterms(e, vs), e.to_str()
