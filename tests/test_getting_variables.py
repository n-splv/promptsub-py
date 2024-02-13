from promptsub import Prompt
import promptsub.special_chatacters as sc
from promptsub.types import RequiredAndOptionalVariables


class TestGettingVariables:

    def test_correct_length(self):
        for i in range(10):
            template = "." + (sc.TEMPLATE.SEPARATOR + ".") * i
            assert len(Prompt(template).variables) == i + 1

    def test_simple(self):
        template = "{required} [{optional}]"
        output = [
            RequiredAndOptionalVariables({"required"}, {"optional"}),
        ]
        assert Prompt(template).variables == output

    def test_first_option_empty(self):
        template = "Nothing in here | {required} | [{optional}]"
        output = [
            RequiredAndOptionalVariables(set(), set()),
            RequiredAndOptionalVariables({"required"}, set()),
            RequiredAndOptionalVariables(set(), {"optional"}),
        ]
        assert Prompt(template).variables == output

    def test_multiple_optional(self):
        template = "{var_1} is needed, [{var_2} [and {var_3}] aren't] | {var_4}"
        output = [
            RequiredAndOptionalVariables({"var_1"}, {"var_2", "var_3"}),
            RequiredAndOptionalVariables({"var_4"}, set()),
        ]
        assert Prompt(template).variables == output

    def test_multiple_required_with_options(self):
        template = "{~var_1} and {var_2=value_2} and {~var_3=value_3}|.|."
        output = [
            RequiredAndOptionalVariables({"var_1", "var_2", "var_3"}, set()),
            RequiredAndOptionalVariables(set(), set()),
            RequiredAndOptionalVariables(set(), set()),
        ]
        assert Prompt(template).variables == output

    def test_no_variables(self):
        template = "I am stability"
        output = [RequiredAndOptionalVariables(set(), set())]
        assert Prompt(template).variables == output

    def test_repetitions(self):
        template = "{var_1} [{var_1} [{var_1}]] {var_1} | and again {var_1}"
        output = [
            RequiredAndOptionalVariables({"var_1"}, {"var_1"}),
            RequiredAndOptionalVariables({"var_1"}, set()),
        ]
        assert Prompt(template).variables == output
