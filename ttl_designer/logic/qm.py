"""Minimización Quine-McCluskey con método de Petrick.

Cada etapa queda registrada en ``QMTrace`` para alimentar la explicación del
diseño: agrupamiento por número de unos, combinaciones por iteración,
implicantes primos, tabla de cobertura, esenciales y selección final.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ast import Const, Expr, Not, Var, make_and, make_or

# Límite de productos intermedios en Petrick antes de caer a cobertura voraz.
PETRICK_LIMIT = 20_000


@dataclass(frozen=True, order=True)
class Implicant:
    """Cubo: ``value`` en las posiciones fijas, ``dashes`` marca las libres."""

    value: int
    dashes: int

    def covers(self, m: int) -> bool:
        return (m & ~self.dashes) == self.value

    def minterms(self, n: int) -> list[int]:
        return [m for m in range(1 << n) if self.covers(m)]

    def literal_count(self, n: int) -> int:
        return n - bin(self.dashes).count("1")

    def pattern(self, n: int) -> str:
        """Notación clásica: ``1-0`` con el MSB a la izquierda."""
        out = []
        for i in range(n - 1, -1, -1):
            bit = 1 << i
            out.append("-" if self.dashes & bit else str((self.value >> i) & 1))
        return "".join(out)

    def to_expr(self, variables: list[str]) -> Expr:
        n = len(variables)
        lits: list[Expr] = []
        for i, name in enumerate(variables):
            bit = 1 << (n - 1 - i)
            if self.dashes & bit:
                continue
            lits.append(Var(name) if self.value & bit else Not(Var(name)))
        return make_and(lits) if lits else Const(True)


@dataclass
class QMTrace:
    n_vars: int
    minterms: list[int]
    dont_cares: list[int]
    # columns[k] = implicantes de la iteración k agrupados por número de unos
    columns: list[dict[int, list[Implicant]]] = field(default_factory=list)
    # combinaciones realizadas: (iteración, a, b, resultado)
    merges: list[tuple[int, Implicant, Implicant, Implicant]] = field(default_factory=list)
    prime_implicants: list[Implicant] = field(default_factory=list)
    # minterm -> implicantes primos que lo cubren (sin don't-cares)
    coverage: dict[int, list[Implicant]] = field(default_factory=dict)
    essential: list[Implicant] = field(default_factory=list)
    method: str = "trivial"  # trivial | essential | petrick | greedy
    petrick_alternatives: int = 0
    selected: list[Implicant] = field(default_factory=list)


@dataclass
class QMResult:
    cover: list[Implicant]
    trace: QMTrace

    def to_expr(self, variables: list[str]) -> Expr:
        if not self.cover:
            return Const(False)
        terms = [imp.to_expr(variables) for imp in self.cover]
        if any(isinstance(t, Const) for t in terms):
            return Const(True)
        return make_or(terms)


def minimize(n_vars: int, minterms: list[int], dont_cares: list[int] | None = None) -> QMResult:
    dont_cares = sorted(set(dont_cares or []))
    ms = sorted(set(minterms))
    limit = 1 << n_vars
    bad = [m for m in ms + dont_cares if not 0 <= m < limit]
    if bad:
        raise ValueError(f"minterms fuera de rango para {n_vars} variables: {bad}")
    overlap = set(ms) & set(dont_cares)
    if overlap:
        raise ValueError(f"minterms declarados también como don't-care: {sorted(overlap)}")

    trace = QMTrace(n_vars, ms, dont_cares)
    if not ms:
        return QMResult([], trace)

    primes = _prime_implicants(n_vars, ms + dont_cares, trace)
    trace.prime_implicants = sorted(primes)

    coverage = {m: [p for p in trace.prime_implicants if p.covers(m)] for m in ms}
    trace.coverage = coverage

    essential = sorted({ps[0] for ps in coverage.values() if len(ps) == 1})
    trace.essential = essential
    remaining = [m for m in ms if not any(e.covers(m) for e in essential)]

    if not remaining:
        trace.method = "essential"
        selected = essential
    else:
        candidates = [p for p in trace.prime_implicants if p not in essential]
        chosen = _petrick(remaining, candidates, n_vars, trace)
        selected = sorted(set(essential) | set(chosen))

    trace.selected = selected
    return QMResult(selected, trace)


def merge_pair(a: Implicant, b: Implicant) -> Implicant | None:
    """Combina dos cubos que difieren en exactamente un bit fijo; si no, None."""
    if a.dashes != b.dashes:
        return None
    diff = a.value ^ b.value
    if diff == 0 or diff & (diff - 1):
        return None
    return Implicant(a.value & ~diff, a.dashes | diff)


def _prime_implicants(n: int, terms: list[int], trace: QMTrace) -> set[Implicant]:
    current = {Implicant(t, 0) for t in terms}
    primes: set[Implicant] = set()
    iteration = 0
    while current:
        groups: dict[int, list[Implicant]] = {}
        for imp in sorted(current):
            groups.setdefault(bin(imp.value).count("1"), []).append(imp)
        trace.columns.append(groups)

        used: set[Implicant] = set()
        nxt: set[Implicant] = set()
        keys = sorted(groups)
        for k in keys:
            for a in groups[k]:
                for b in groups.get(k + 1, []):
                    merged = merge_pair(a, b)
                    if merged is None:
                        continue
                    used.update((a, b))
                    if merged not in nxt:
                        trace.merges.append((iteration, a, b, merged))
                    nxt.add(merged)
        primes |= current - used
        current = nxt
        iteration += 1
    return primes


def _cost(sel: frozenset[Implicant], n: int) -> tuple[int, int]:
    return len(sel), sum(p.literal_count(n) for p in sel)


def _petrick(
    remaining: list[int], candidates: list[Implicant], n: int, trace: QMTrace
) -> list[Implicant]:
    # Producto de sumas: cada minterm exige al menos uno de sus implicantes.
    products: set[frozenset[Implicant]] = {frozenset()}
    for m in remaining:
        options = [p for p in candidates if p.covers(m)]
        expanded: set[frozenset[Implicant]] = set()
        for prod in products:
            if any(p in prod for p in options):
                expanded.add(prod)
            else:
                for p in options:
                    expanded.add(prod | {p})
        products = _absorb(expanded)
        if len(products) > PETRICK_LIMIT:
            trace.method = "greedy"
            return _greedy(remaining, candidates, n)

    trace.method = "petrick"
    trace.petrick_alternatives = len(products)
    best = min(products, key=lambda s: (_cost(s, n), sorted(s)))
    return sorted(best)


def _absorb(products: set[frozenset[Implicant]]) -> set[frozenset[Implicant]]:
    """Ley de absorción: X + X·Y = X."""
    ordered = sorted(products, key=len)
    kept: list[frozenset[Implicant]] = []
    for p in ordered:
        if not any(k <= p for k in kept):
            kept.append(p)
    return set(kept)


def _greedy(remaining: list[int], candidates: list[Implicant], n: int) -> list[Implicant]:
    left = set(remaining)
    chosen: list[Implicant] = []
    while left:
        best = max(
            candidates,
            key=lambda p: (sum(p.covers(m) for m in left), -p.literal_count(n), -p.value),
        )
        chosen.append(best)
        left = {m for m in left if not best.covers(m)}
    return chosen
