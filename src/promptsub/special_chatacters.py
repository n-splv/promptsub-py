from string import ascii_letters, digits
from typing import NamedTuple


class TemplateBoundaries(NamedTuple):
    OPENING: str = "["
    CLOSING: str = "]"
    SEPARATOR: str = "|"


class VariableBoundaries(NamedTuple):
    OPENING: str = "{"
    CLOSING: str = "}"


class VariableOptions(NamedTuple):
    MUTE: str = "~"
    EQ: str = "="


TEMPLATE = TemplateBoundaries()
VARIABLE = VariableBoundaries()

VARIABLE_NAME_SAFE = ascii_letters + digits + "_"
VARIABLE_OPTIONS = VariableOptions()
