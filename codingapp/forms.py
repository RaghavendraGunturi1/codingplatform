from django import forms
from .models import Module, Question
import json

class ModuleForm(forms.ModelForm):
    """ Form for creating and editing Modules """
    class Meta:
        model = Module
        fields = ["title", "description"]

class QuestionForm(forms.ModelForm):
    """ Form for creating and editing Questions """
    test_cases = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "cols": 50, "placeholder": "Enter test cases in JSON format."}),
        help_text="Format: [{'input': '1 2', 'expected_output': '3'}, {'input': '2 3', 'expected_output': '5'}]"
    )

    class Meta:
        model = Question
        fields = ['title', 'description', 'module', 'test_cases']

    def clean_test_cases(self):
        """ Validate and convert test cases from string to JSON """
        data = self.cleaned_data['test_cases'].strip()  # Remove extra spaces
        if not data:
            raise forms.ValidationError("Test cases cannot be empty.")

        try:
            test_cases = json.loads(data)
            if not isinstance(test_cases, list):
                raise forms.ValidationError("Test cases should be a list of dictionaries.")
            for case in test_cases:
                if not isinstance(case, dict) or "input" not in case or "expected_output" not in case:
                    raise forms.ValidationError("Each test case must have 'input' and 'expected_output' keys.")
            return test_cases  # Return as a proper Python list
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for test cases. Please check your syntax.")
