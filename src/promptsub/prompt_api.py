from __future__ import annotations
from functools import cached_property

from attrs import (
    Factory,
    field,
    frozen,
    validators,
)

from promptsub.prompt_components.template import Template
from promptsub.errors import ParametersTypeError
from promptsub.types import (
    InputParams,
    RequiredAndOptionalVariables,
    ValidatedParams,
)


def _init_template(self: Prompt) -> Template:
    """
    Manual type check because `attrs.validators` is a bit broken:
    https://github.com/python-attrs/attrs/issues/1237

    Can be replaced with a simple lambda if it gets fixed.
    """
    if not isinstance(self.template_text, str):
        err_message = "Template text must be a string"
        raise TypeError(err_message)

    return Template(input_text=self.template_text)


@frozen
class Prompt:
    """
    Prompt is created with a string conforming to the `promptsub` syntax:
    https://github.com/n-splv/promptsub-py?tab=readme-ov-file#syntax-guide

    Syntax is checked during the instantiation, and a `PromptSyntaxError` can
    be raised.

    Basic usage:
    ---
    template = "Say hello [to {name}]"
    prompt = Prompt(template)

    params = {"name": "John"}
    result = prompt.substitute(params)  # Say hello to John
    """

    template_text: str = field(validator=validators.instance_of(str))

    _template: Template = field(
        init=False,
        repr=False,
        default=Factory(_init_template, takes_self=True)
    )

    def substitute(self,
                   params: InputParams,
                   postprocess_whitespace_reduction: bool = True) -> str:
        """
        Insert parameters into the template, returning the message for model.
        If parameters violate the expected typing, a `ParametersTypeError` is
        raised.

        If any of the required variables is not provided, result will be an
        empty string.
        """
        params = _validate_params(params)
        result = self._template.substitute(params)

        if postprocess_whitespace_reduction:
            result = " ".join(result.split())

        return result

    @cached_property
    def variables(self) -> list[RequiredAndOptionalVariables]:
        """
        Get the names (keys) of all Variables used in a Template.

        Returns list of NamedTuples. Each NamedTuple has attributes
        `required` and `optional`, which are sets of strings.

        A prompt template might consist of multiple alternatives (options)
        divided by separators "|":

        > t1 = "Write this if {var_1} and {var_2} | or this if {var_3}"

        This template will return a non-empty string only if substituted
        with both (`var_1` AND `var_2`) OR if substituted with `var_3`.
        Therefore:

        > Prompt(t1).variables
        [
            (required={'var_2', 'var_1'}, optional=set()),
            (required={'var_3'}, optional=set())
        ]

        The Variables that are not required at Template's top level are
        put into `optional` set regardless of depth of their nesting:

        > t2 = "{var_1} is needed, [but {var_2} [and {var_3}] not so much]"
        > Prompt(t2).variables
        [
            (required={'var_1'}, optional={'var_3', 'var_2'})
        ]
        """
        return self._template.variable_keys


def _validate_params(params: dict) -> ValidatedParams:
    """
    Check that the keys are str and the values are str, int or float.
    Convert the values to str.
    """
    for key, value in params.items():

        if not isinstance(key, str):
            err_message = f"Key {key} is not a string"
            raise ParametersTypeError(err_message)

        match value:
            case str():
                pass
            case int() | float():
                params[key] = str(value)
            case _:
                err_message = f"Key {key} has a non-string value"
                raise ParametersTypeError(err_message)

    return params
