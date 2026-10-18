import random

import pytest

from ttl_designer.logic.ast import And, Expr, Not, Or, Var, Xor


def random_expr(rng: random.Random, variables: list[str], depth: int = 4) -> Expr:
    if depth == 0 or rng.random() < 0.25:
        return Var(rng.choice(variables))
    op = rng.choice(["not", "and", "or", "xor"])
    if op == "not":
        return Not(random_expr(rng, variables, depth - 1))
    args = tuple(random_expr(rng, variables, depth - 1) for _ in range(rng.randint(2, 3)))
    return {"and": And, "or": Or, "xor": Xor}[op](args)


@pytest.fixture
def rng() -> random.Random:
    return random.Random(1234)
