from __future__ import annotations

from pydantic import BaseModel, Field

from ..bom import Bom, BomOptions
from ..drc import DrcReport
from ..models.netlist import Netlist
from ..models.physical import PhysicalDesign


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


class MapRequest(BaseModel):
    equations: str = Field(examples=["S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)"])
    dont_cares: dict[str, list[int]] = Field(default_factory=dict)
    strategies: list[str] | None = Field(
        default=None, description="subconjunto de estrategias; por defecto todas"
    )
    allow_open_collector: bool = False
    allow_schmitt: bool = False
    excluded_parts: list[str] = Field(default_factory=list)
    bom: BomOptions = Field(default_factory=BomOptions)


class CandidateOut(BaseModel):
    source: str
    strategy: str
    ic_count: int | None
    depth: int | None
    gate_count: int | None
    parts: dict[str, int]
    absorbed: int
    equivalent: bool
    error: str | None


class MapResponse(BaseModel):
    inputs: list[str]
    outputs: list[str]
    candidates: list[CandidateOut]
    selected: CandidateOut | None
    design: PhysicalDesign | None
    connections: dict[str, list[str]]
    warnings: list[str]
    drc: DrcReport | None
    bom: Bom | None
