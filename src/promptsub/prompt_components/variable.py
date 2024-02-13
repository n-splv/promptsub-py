from attrs import define

from promptsub import special_chatacters as sc
from promptsub.prompt_components.base import non_init, PromptComponent
from promptsub.errors import (
    InternalError,
    PromptSyntaxError,
    VariableError,
    SyntaxErrorDetails,
)
from promptsub.types import ValidatedParams


@define(kw_only=True)
class Variable(PromptComponent):

    _muted: bool = non_init(default=False)

    _key: str = non_init(default=None)
    _required_value: str = non_init(default=None)

    _key_characters: list[str] = non_init(factory=list, repr=False)
    _required_value_characters: list[str] = non_init(factory=list, repr=False)

    def __attrs_post_init__(self):
        """
        Start appending to `_key_characters` first.
        See `self.append` for more info.
        """
        self._input_characters = self._key_characters

    def substitute(self, params: ValidatedParams) -> str:
        if self.end_index is None:
            err_message = "End index must be set before substitution"
            raise InternalError(err_message)

        result = params.get(self._key, "")
        if result == "":
            raise VariableError

        if self._required_value and result != self._required_value:
            raise VariableError

        if self._muted:
            result = ""

        return result

    def append(self, char: str):
        """
        We are appending to one of the two destination arrays:
        `_key_characters` or `_required_value_characters`.

        When appending to `_key_characters` we check if the
        char is among those that set options for Variable and
        whether it's allowed to be used in a Variable key.
        """

        if self._input_characters is self._required_value_characters:
            super().append(char)

        elif char in sc.VARIABLE_OPTIONS:
            self._process_option(char)

        elif char not in sc.VARIABLE_NAME_SAFE:
            err_message = "Char %s not allowed in variable key"
            self._raise_detailed_syntax_error(err_message % char, char)

        else:
            super().append(char)

    @property
    def key(self) -> str | None:
        return self._key

    def _before_close(self) -> None:
        # Order of calls matters
        self._set_required_value()
        self._set_key()

    def _set_key(self) -> None:
        if not self._key_characters:
            err_message = "Variable key can not be empty"
            raise PromptSyntaxError(err_message)

        self._key = "".join(self._key_characters)
        self._key_characters = []

    def _set_required_value(self) -> None:
        if not self._required_value_characters:
            if self._input_characters is self._required_value_characters:
                err_message = "Required value can not be empty"
                self._raise_detailed_syntax_error(err_message)
            return

        self._required_value = "".join(self._required_value_characters)
        self._required_value_characters = []

    def _process_option(self, char: str) -> None:
        match char:
            case sc.VARIABLE_OPTIONS.MUTE:
                self._mute()
            case sc.VARIABLE_OPTIONS.EQ:
                # Subsequent chars will be appended to another array
                self._input_characters = self._required_value_characters

    def _mute(self) -> None:
        if len(self._input_characters) == 0 and not self._muted:
            self._muted = True
            return

        err_message = "A mute symbol is only allowed in the beginning"
        self._raise_detailed_syntax_error(
            err_message,
            sc.VARIABLE_OPTIONS.MUTE
        )

    def _raise_detailed_syntax_error(self,
                                     err_message: str,
                                     character: str = None) -> None:
        err_detail_characters = [
            sc.VARIABLE.OPENING,
            sc.VARIABLE_OPTIONS.MUTE if self._muted else "",
            *self._key_characters,
            character or "",
        ]
        err_details = SyntaxErrorDetails(
            text="".join(err_detail_characters),
            offset=len(err_detail_characters)
        )
        raise PromptSyntaxError(err_message, err_details)
