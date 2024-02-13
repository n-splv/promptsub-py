from string import punctuation

import pytest

from promptsub import Prompt
from promptsub import special_chatacters as sc


def generate_fake_params(n: int) -> tuple[dict, dict, dict]:
    """
    Returns 3 dicts:
    all_: {"var_1": "value_1", "var_2": "value_2", ...}
    even: {"var_2": "value_2", "var_4": "value_4", ...}
    odd:  {"var_1": "value_1", "var_3": "value_3", ...}
    """
    odd = {}
    even = {}
    for i in range(1, 1 + n):
        kw_pair = {f"var_{i}": f"value_{i}"}
        if i % 2:
            odd.update(kw_pair)
        else:
            even.update(kw_pair)
    all_ = odd | even
    return all_, even, odd


params_all, params_even, params_odd = generate_fake_params(10)


class TestVariable:

    @pytest.mark.parametrize("template, params, output", (
            ("{var_1}", params_odd, "value_1"),
            ("{var_1}", params_even, ""),
    ))
    def test_basic(self, template, params, output):
        assert Prompt(template).substitute(params) == output

    def test_muted(self):
        template = "Show this {~but_not_this}"
        params = {"but_not_this": "value"}
        output = "Show this"
        assert Prompt(template).substitute(params) == output

    def test_empty_value(self):
        template = "{is_this_expanded_to_an_empty_stting} - no"
        params = {"is_this_expanded_to_an_empty_stting": ""}
        output = ""
        assert Prompt(template).substitute(params) == output

    def test_with_weird_value(self):
        template = "Why not {var}"
        for value in punctuation:
            params = {"var": value}
            output = "Why not %s" % value
            assert Prompt(template).substitute(params) == output

    @pytest.mark.parametrize("reduce_whitespaces, output", (
            (True, "did someone say whitespaces ?"),
            (False, "  did someone \t say \n whitespaces \r?"),
    ))
    def test_reduce_whitespaces_in_value(self, reduce_whitespaces, output):
        template = "{var}"
        params = {"var": "  did someone \t say \n whitespaces \r?"}
        result = Prompt(template).substitute(params, reduce_whitespaces)
        assert result == output

    def test_weird_keys(self):
        output = "some_value"
        for key in ("_", "1", "__1"):
            template = "{%s}" % key
            params = {key: output}
            assert Prompt(template).substitute(params) == output

    @pytest.mark.parametrize("params, output", (
            ({"weather": "hot"}, "Call me only when it's hot outside"),
            ({"weather": "cold"}, ""),
            ({}, ""),
    ))
    def test_required_value(self, params, output):
        template = "Call me only when it's {weather=hot} outside"
        assert Prompt(template).substitute(params) == output

    @pytest.mark.parametrize("params, output", (
            ({"sleep": "well"}, "Let's go for a run!"),
            ({"sleep": "bad"}, "Stay in bed"),
    ))
    def test_muted_required_value(self, params, output):
        template = "{~sleep=well} Let's go for a run! | Stay in bed"
        assert Prompt(template).substitute(params) == output

    def test_alternative_to_required_value(self):
        template = "Are these identical? [Sure! {~var_1} | {var_2=Sure!}]"
        output = "Are these identical? Sure!"
        params_list = [{"var_1": "Sure!"}, {"var_2": "Sure!"}]
        for params in params_list:
            assert Prompt(template).substitute(params) == output

    def test_non_ascii_characters_in_required_value(self):
        forbidden_chars = sc.TEMPLATE + sc.VARIABLE
        chars_to_test = ["Я", "我", "أنا"] + [
            char for char in punctuation if char not in forbidden_chars
        ]
        for char in chars_to_test:
            template = "This should work {var=%s}" % char
            params = {"var": char}
            output = "This should work %s" % char
            assert Prompt(template).substitute(params) == output


class TestTemplate:

    def test_basic(self):
        template = "[This should just be expanded]"
        output = "This should just be expanded"
        assert Prompt(template).substitute({}) == output

    @pytest.mark.parametrize("params, output", (
            (params_odd, "Now it depends on value_1"),
            (params_even, "Now"),
    ))
    def test_variable(self, params, output):
        template = "Now [it depends on {var_1}]"
        assert Prompt(template).substitute(params) == output

    def test_muted_variable(self):
        template = "[I know something {~secret}]"
        params = {"secret": "about you"}
        output = "I know something"
        assert Prompt(template).substitute(params) == output

    def test_deep_nesting(self):
        template = """
        [Insane? [- Yes, [but [should [still [be [ok.[.[.[.]]]]]]]]]]
        """
        output = "Insane? - Yes, but should still be ok...."
        assert Prompt(template).substitute({}) == output

    @pytest.mark.parametrize("params, output", (
            (params_all, "Only if value_1 and value_2 are known"),
            (params_even, ""),
            (params_odd, "")
    ))
    def test_multiple_variables(self, params, output):
        template = "Only if {var_1} and {var_2} are known"
        assert Prompt(template).substitute(params) == output


class TestSeparator:

    @pytest.mark.parametrize("params, output", (
            (params_all, "Blue if value_1"),
            (params_even, "Red if value_2"),
            (params_odd, "Blue if value_1"),
    ))
    def test_basic(self, params, output):
        template = "Blue if {var_1} | Red if {var_2}"
        assert Prompt(template).substitute(params) == output

    def test_unreachable(self):
        template = "Constant | this is unreachable {var}"
        assert Prompt(template).substitute({"var": "value"}) == "Constant"

    @pytest.mark.parametrize("params, output", (
            (params_all, "Vote for me"),
            (params_even, "Vote for you"),
            (params_odd, "Vote for me"),
    ))
    def test_nested(self, params, output):
        template = "Vote for [me {~var_1} | you {~var_2}]"
        assert Prompt(template).substitute(params) == output


class TestMisc:

    def test_no_whitespace_reduction(self):
        template = "Don't mess my \n {var}"
        params = {"var": "a  e  s  t  h  e  t  i  c  s"}
        output = "Don't mess my \n a  e  s  t  h  e  t  i  c  s"
        result = Prompt(template).substitute(
            params,
            postprocess_whitespace_reduction=False
        )
        assert result == output
