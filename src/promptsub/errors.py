from typing import NamedTuple


class InternalError(BaseException):
    """
    The inner logic of the library got broken
    """


class VariableError(BaseException):
    """
    Variable is not in parameters or its value doesn't match the required one.
    Must always be expected.
    """


class ParametersTypeError(BaseException):
    """
    Provided parameters violate the expected typing
    """


class SyntaxErrorDetails(NamedTuple):
    """
    Used to point to the character that caused `PromptSyntaxError`.
    Lineno and offset start at 1
    """
    text: str
    offset: int
    filename: str = None
    lineno: int = 1


class PromptSyntaxError(SyntaxError):
    def __init__(self,
                 message: str = None,
                 details: SyntaxErrorDetails = None):

        if not details:
            super().__init__(message)
            return

        # Must follow specific order for SyntaxError
        details = (
            details.filename,
            details.lineno,
            details.offset,
            details.text
        )
        super().__init__(message, details)
