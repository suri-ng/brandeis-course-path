from __future__ import annotations
from typing import Literal
from typing_extensions import Self
from pydantic import BaseModel, Field, model_validator

class PrereqGroup(BaseModel):
    operator: Literal["AND", "OR"]
    items: list[str | PrereqGroup] = Field(default_factory=list)

class Course(BaseModel):
    code: str
    title: str
    description: str = ""
    core_req: list[str] = Field(default_factory=list)
    pre_req: PrereqGroup | None = None # PrereqGroup can already contains nested groups

class Node(BaseModel):
    code: str
    data: Course | None = None
    is_external: bool = False

    @model_validator(mode="after")
    def check_external_data(self) -> Self:
        if self.is_external != (self.data is None):
            raise ValueError(
                "External nodes must have no course data; listed nodes must have course data."
            )
        return self

    @model_validator(mode="after")
    def check_code_match(self) -> Self:
        if not self.is_external:
            if self.code != self.data.code:
                raise ValueError(
                    "Listed node's code must match data's Course code."
                )

        return self

class Edge(BaseModel):
    source: str #code
    target: str #code
    line_style: Literal["solid","dashed"] # only represents visual

class CourseGraph(BaseModel):
    nodes: list[Node]
    edges: list[Edge]
