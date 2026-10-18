"""Parser recursivo descendente de expresiones booleanas.

Gramática (precedencia de menor a mayor):

    equations := equation ((';' | NEWLINE) equation)*
    equation  := IDENT '=' expr
    expr      := xor_e (OR xor_e)*                OR  = + | ∨
    xor_e     := and_e (XOR and_e)*               XOR = ^ ⊕
    and_e     := unary ((AND)? unary)*            AND = · * & ∧   (o yuxtaposición)
    unary     := NOT unary | postfix              NOT = ! ~ ¬
    postfix   := atom "'"*
    atom      := IDENT | '0' | '1' | '(' expr ')'

Los identificadores pueden tener varios caracteres, así que ``AB`` es una sola
variable; para el producto se escribe ``A B``, ``A·B`` o ``A*B``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ast import And, Const, Expr, NAry, Not, Or, Var, Xor, make_and, make_or


class ParseError(ValueError):
    def __init__(self, message: str, pos: int, text: str):
        self.pos = pos
        self.text = text
        super().__init__(f"{message} (posición {pos})")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    pos: int


_TOKEN_RE = re.compile(
    r"""
    (?P<WS>[ \t\r]+)
  | (?P<NL>\n)
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<CONST>[01])
  | (?P<OR>[+|∨])
  | (?P<XOR>[\^⊕])
  | (?P<AND>[·*&∧.])
  | (?P<NOT>[!~¬])
  | (?P<PRIME>['’])
  | (?P<LPAREN>\()
  | (?P<RPAREN>\))
  | (?P<EQ>=)
  | (?P<SEMI>;)
    """,
    re.VERBOSE,
)

# Tokens que pueden iniciar un factor; habilitan el AND implícito.
_FACTOR_START = {"IDENT", "CONST", "NOT", "LPAREN"}


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise ParseError(f"carácter inesperado {text[pos]!r}", pos, text)
        kind = m.lastgroup
        assert kind is not None
        if kind != "WS":
            kind = "SEP" if kind in ("NL", "SEMI") else kind
            tokens.append(Token(kind, m.group(), pos))
        pos = m.end()
    tokens.append(Token("EOF", "", len(text)))
    return tokens


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.tokens = tokenize(text)
        self.i = 0

    @property
    def tok(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        t = self.tokens[self.i]
        self.i += 1
        return t

    def expect(self, kind: str, what: str) -> Token:
        if self.tok.kind != kind:
            found = self.tok.value or "fin de entrada"
            raise ParseError(f"se esperaba {what}, se encontró {found!r}", self.tok.pos, self.text)
        return self.advance()

    def skip_separators(self) -> None:
        while self.tok.kind == "SEP":
            self.advance()

    def equations(self) -> list[tuple[str, Expr]]:
        result: list[tuple[str, Expr]] = []
        self.skip_separators()
        while self.tok.kind != "EOF":
            name = self.expect("IDENT", "nombre de salida").value
            self.expect("EQ", "'='")
            expr = self.expr()
            result.append((name, expr))
            if self.tok.kind not in ("SEP", "EOF"):
                raise ParseError(f"token inesperado {self.tok.value!r}", self.tok.pos, self.text)
            self.skip_separators()
        if not result:
            raise ParseError("no hay ecuaciones", 0, self.text)
        return result

    def expr(self) -> Expr:
        terms = [self.xor_e()]
        while self.tok.kind == "OR":
            self.advance()
            terms.append(self.xor_e())
        return make_or(_flatten(terms, Or))

    def xor_e(self) -> Expr:
        terms = [self.and_e()]
        while self.tok.kind == "XOR":
            self.advance()
            terms.append(self.and_e())
        return terms[0] if len(terms) == 1 else Xor(tuple(_flatten(terms, Xor)))

    def and_e(self) -> Expr:
        factors = [self.unary()]
        while True:
            if self.tok.kind == "AND":
                self.advance()
            elif self.tok.kind not in _FACTOR_START:
                break
            factors.append(self.unary())
        return make_and(_flatten(factors, And))

    def unary(self) -> Expr:
        if self.tok.kind == "NOT":
            self.advance()
            return Not(self.unary())
        return self.postfix()

    def postfix(self) -> Expr:
        e = self.atom()
        while self.tok.kind == "PRIME":
            self.advance()
            e = Not(e)
        return e

    def atom(self) -> Expr:
        t = self.tok
        if t.kind == "IDENT":
            self.advance()
            return Var(t.value)
        if t.kind == "CONST":
            self.advance()
            return Const(t.value == "1")
        if t.kind == "LPAREN":
            self.advance()
            e = self.expr()
            self.expect("RPAREN", "')'")
            return e
        found = t.value or "fin de entrada"
        raise ParseError(f"se esperaba un operando, se encontró {found!r}", t.pos, self.text)


def _flatten(items: list[Expr], cls: type[NAry]) -> list[Expr]:
    out: list[Expr] = []
    for it in items:
        if isinstance(it, cls):
            out.extend(it.args)
        else:
            out.append(it)
    return out


def parse_expression(text: str) -> Expr:
    p = _Parser(text)
    e = p.expr()
    p.skip_separators()
    if p.tok.kind != "EOF":
        raise ParseError(f"token inesperado {p.tok.value!r}", p.tok.pos, text)
    return e


def parse_equations(text: str) -> list[tuple[str, Expr]]:
    """Parsea ``Y = expr`` separadas por ``;`` o salto de línea."""
    eqs = _Parser(text).equations()
    names = [n for n, _ in eqs]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise ParseError(f"salidas repetidas: {', '.join(sorted(dup))}", 0, text)
    return eqs
