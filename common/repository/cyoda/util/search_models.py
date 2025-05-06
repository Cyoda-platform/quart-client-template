from dataclasses import dataclass
from typing import List

@dataclass
class Condition:
    type: str
    jsonPath: str
    operatorType: str
    value: str

@dataclass
class SearchConditionRequest:
    type: str
    operator: str
    conditions: List[Condition]