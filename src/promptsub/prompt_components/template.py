from __future__ import annotations
from typing import Optional

from attrs import define

from promptsub import special_chatacters as sc
from promptsub.prompt_components.base import non_init, PromptComponent
from promptsub.prompt_components.variable import Variable
from promptsub.errors import (
    InternalError,
    PromptSyntaxError,
    VariableError,
    SyntaxErrorDetails,
)
from promptsub.types import ValidatedParams, RequiredAndOptionalVariables


@define(kw_only=True)
class Template(PromptComponent):

    input_text: str = None

    _components: list[PromptComponent] = non_init(factory=list)
    _templates: list[Template] = non_init(factory=list, repr=False)
    _variables: list[Variable] = non_init(factory=list, repr=False)

    _alternative: Template = non_init(default=None)

    def __attrs_post_init__(self):
        if self.input_text is not None:
            self._parse_and_validate()

    def substitute(self, params: ValidatedParams) -> str:
        """
        1. Check if all the top-level Variables are present in params;
        2. If not, go to `self.alternative` and start again;
        3. If yes, substitute all Templates and Variables from right to left.
        """
        try:
            variable_substitutions = [
                variable.substitute(params) for variable in self._variables
            ]
        except VariableError:
            if self._alternative:
                return self._alternative.substitute(params)
            return ""

        return self._substitute_all_components(params, variable_substitutions)

    @property
    def variable_keys(self) -> list[RequiredAndOptionalVariables]:
        """
        Get the names (keys) of all Variables used in a Template.

        This creates a list of `RequiredAndOptionalVariables`, where each
        instance represents an alternative (option divided by separator "|")
        in the current level of Template.

        The `required` variables are simply created from the current level
        `_variables`. The `_optional` variables are created recursively from
        both the `required` and `optional` variables of the lower-level
        Templates.

        As a result we get NamedTuples in which `required` variables come
        from the single top level and `optional` variables from all the
        nested levels.
        """
        required = {variable.key for variable in self._variables}
        optional = set()

        for child_template in self._templates:
            for child_variable_keys in child_template.variable_keys:
                optional.update(child_variable_keys.required)
                optional.update(child_variable_keys.optional)

        result = [RequiredAndOptionalVariables(required, optional)]
        if self._alternative:
            result += self._alternative.variable_keys
        return result

    def _substitute_all_components(self,
                                   params: ValidatedParams,
                                   variable_substitutions: list[str]) -> str:
        text = self.input_text

        for component in reversed(self._components):
            match component:
                case Template():
                    component_text = component.substitute(params)
                case Variable():
                    component_text = variable_substitutions.pop()
                case _:
                    err_message = "Wrong component type: %s"
                    raise InternalError(err_message % type(component))
            text = "".join((
                text[:component.start_index],
                component_text,
                text[component.end_index:],
            ))

        return text

    def _before_close(self) -> None:
        self.input_text = "".join(self._input_characters)
        self._parse_and_validate()

    def _parse_and_validate(self) -> None:
        """
        Pass the whole Template one level at a time. After running this
        method, our `_components` and `_alternative` attributes obtain
        their final values (can still be an empty list and None though).
        Depending on what we encounter, there are the 3 main logic flows:

        1. A Variable.
        We instantiate it and then append the next characters to it until
        it's closed. A Variable checks every character in real time and
        may raise a `PromptsubSyntaxError`.
        Template should know as little as possible about the internal
        workings of Variable, since they may change independently.
        Hovever, all the scope defining special characters, except the
        `sc.VARIABLE.CLOSING`, are not allowed to be used in Variable.
        When a Variable is closed, we save it to our `_components`.

        2. Another nested Template
        Instantiate it and then append to it all the next characters
        (special or not) until it's closed - no validation is done yet.
        When a Template is closed, it runs its own `_parse_and_validate()`
        method. After that we save it to our `_components`.

        3. A Separator
        At this point we stop the current Template's text and create a
        new Template with its `input_text` being the tail after the
        Separator. This new Template is parsed and after that saved to
        our `_alternative` attribute.
        """

        text = self.input_text
        current_component: Optional[PromptComponent] = None
        nested_template_stack = []

        characters_to_check = sc.TEMPLATE + sc.VARIABLE

        def close_and_save_component(current_index: int,
                                     save_destination: list[PromptComponent]):
            nonlocal current_component

            current_component.close(end_index=current_index + 1)
            self._components.append(current_component)
            save_destination.append(current_component)
            current_component = None

        for i, char in enumerate(text):

            if char not in characters_to_check:
                if current_component is not None:
                    current_component.append(char)
                continue

            match char, current_component:
                case [sc.TEMPLATE.OPENING, None]:
                    current_component = Template(start_index=i)

                case [sc.TEMPLATE.OPENING, Template()]:
                    nested_template_stack.append(...)
                    current_component.append(char)

                case [sc.TEMPLATE.CLOSING, Template()]:
                    if nested_template_stack:
                        nested_template_stack.pop()
                        current_component.append(char)
                        continue
                    close_and_save_component(i, self._templates)

                case [_, Template()]:
                    current_component.append(char)

                case [sc.VARIABLE.OPENING, None]:
                    current_component = Variable(start_index=i)

                case [sc.VARIABLE.CLOSING, Variable()]:
                    close_and_save_component(i, self._variables)

                case [sc.TEMPLATE.SEPARATOR, None]:
                    alt_text = text[i + 1:]
                    self._alternative = Template(input_text=alt_text)
                    self.input_text = text[:i]
                    break

                case _:
                    """
                    sc.TEMPLATE.OPENING, Variable()
                    sc.TEMPLATE.CLOSING, Variable()
                    sc.TEMPLATE.SEPARATOR, Variable()
                    sc.VARIABLE.OPENING, Variable()
                    sc.TEMPLATE.CLOSING, None
                    sc.VARIABLE.CLOSING, None
                    """
                    err_message = f"Wrong special character '%s' position"
                    err_details = SyntaxErrorDetails(text=text, offset=i + 1)
                    raise PromptSyntaxError(err_message % char, err_details)

        # Check after the iteration to deal with repeated separators
        if self.input_text == "":
            raise PromptSyntaxError("A template can not be empty")

        if current_component is not None:
            err_message = "%s not closed" % type(current_component).__name__
            err_details = SyntaxErrorDetails(
                text=text,
                offset=current_component.start_index + 1
            )
            raise PromptSyntaxError(err_message, err_details)
