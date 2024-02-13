from functools import wraps

import pytest

from promptsub import Prompt
from promptsub.errors import ParametersTypeError, PromptSyntaxError
from promptsub import special_chatacters as sc


def raises(exception):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with pytest.raises(exception):
                func(*args, **kwargs)
        return wrapper
    return decorator


class TestVariable:

    @raises(PromptSyntaxError)
    @pytest.mark.parametrize("template", (
        "{}",
        "{=some_value}",
        "{.}",
        "{Я}",
        "{with whitespace}",
    ))
    def test_bad_keys(self, template):
        Prompt(template)

    @raises(PromptSyntaxError)
    def test_empty_required_value(self):
        template = "{var=}"
        Prompt(template)

    @raises(PromptSyntaxError)
    @pytest.mark.parametrize("template", (
        "{~~var}",
        "{var~}",
        "{v~ar}",
    ))
    def test_muted_in_the_wrong_place(self, template):
        Prompt(template)

    @raises(PromptSyntaxError)
    @pytest.mark.parametrize("template", (
        "{" + sc.TEMPLATE.OPENING,
        "{" + sc.TEMPLATE.CLOSING,
        "{" + sc.TEMPLATE.SEPARATOR,
        "{" + sc.VARIABLE.OPENING,
    ))
    def test_not_allowed_characters(self, template):
        Prompt(template)


class TestTemplate:
    @raises(PromptSyntaxError)
    @pytest.mark.parametrize("template", (
        "{",
        "[",
    ))
    def test_component_not_closed(self, template):
        Prompt(template)

    @raises(PromptSyntaxError)
    @pytest.mark.parametrize("template", (
        "",
        "[]",
        "Test []",
        "Test |",
        "|"
    ))
    def test_empty_template(self, template):
        Prompt(template)

    @raises(TypeError)
    @pytest.mark.parametrize("template", (
        None,
        type("Foo", (), {})(),
        lambda: ...,
        tuple('a'),
        1,
        0.0
    ))
    def test_bad_template_type(self, template):
        Prompt(template)


class TestParams:

    @raises(ParametersTypeError)
    @pytest.mark.parametrize("value", (
            None,
            type("Foo", (), {})(),
            lambda: ...,
            tuple(),
    ))
    def test_bad_values(self, value):
        Prompt(".").substitute({"var": value})  # noqa

    @pytest.mark.parametrize("value", (
            1,
            1.0,
            False,
            "a",
    ))
    def test_ok_values(self, value):
        Prompt(".").substitute({"var": value})

    @raises(ParametersTypeError)
    @pytest.mark.parametrize("key", (
            None,
            type("Foo", (), {})(),
            lambda: ...,
            tuple(),
            1,
            1.0,
            False,
    ))
    def test_bad_keys(self, key):
        Prompt(".").substitute({key: "value"})


class TestNotErrors:

    def test_variable_options_outside_variable(self):
        template = "Outside we are free" + "".join(sc.VARIABLE_OPTIONS)
        Prompt(template)
