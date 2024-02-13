from typing import NamedTuple, TypeAlias

InputParams: TypeAlias = dict[str, str | int | float]
ValidatedParams: TypeAlias = dict[str, str]


class RequiredAndOptionalVariables(NamedTuple):
    required: set[str]
    optional: set[str]

    def __repr__(self) -> str:
        return f"(required={self.required}, optional={self.optional})"
