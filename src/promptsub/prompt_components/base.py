from abc import ABC, abstractmethod
from functools import partial

from attrs import define, field

from promptsub.errors import InternalError
from promptsub.types import ValidatedParams


non_init = partial(field, init=False)


@define
class PromptComponent(ABC):

    # Default is None because not all `Templates` need `start_index` -
    # only the first options of the nested ones do.
    start_index: int = None

    _end_index: int = non_init(default=None)
    _input_characters: list[str] = non_init(factory=list, repr=False)

    def append(self, char: str) -> None:
        if self.start_index is None:
            err_message = "Start index must be set before appending"
            raise InternalError(err_message)

        if self._end_index is not None:
            err_message = "No appending after the end index is set"
            raise InternalError(err_message)

        self._input_characters.append(char)

    def close(self, end_index: int) -> None:
        self._before_close()
        self._input_characters = []
        self._end_index = end_index

    @property
    def end_index(self) -> int | None:
        return self._end_index

    @abstractmethod
    def substitute(self, params: ValidatedParams) -> str:
        pass

    @abstractmethod
    def _before_close(self) -> None:
        pass
