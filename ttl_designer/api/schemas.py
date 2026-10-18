from __future__ import annotations

from pydantic import BaseModel, Field

from ..models.netlist import Netlist


class AnalyzeRequest(BaseModel):
    equations: str = Field(examples=["Y = A·B' + A·C + B·C'"])
    # don't-cares por salida, como índices de fila (convención Σm, primera variable = MSB)
    dont_cares: dict[str, list[int]] = Field(default_factory=dict)


class ImplicantOut(BaseModel):
    pattern: str
    term: str
    minterms: list[int]


class MinimizationOut(BaseModel):
    output: str
    original: str
    minterms: list[int]
    dont_cares: list[int]
    prime_implicants: list[ImplicantOut]
    essential: list[ImplicantOut]
    method: str
    minimized: str


class AnalyzeResponse(BaseModel):
    inputs: list[str]
    outputs: list[str]
    truth_table: list[list[int]]
    minimization: list[MinimizationOut]
    netlist: Netlist
    logic_depth: int
    equivalent: bool
