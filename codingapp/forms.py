from django import forms
from .models import Module, Question
import json

class ModuleForm(forms.ModelForm):
    """Form for creating and editing Modules"""
    class Meta:
        model = Module
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False  # Match model’s blank=True, null=True

class QuestionForm(forms.ModelForm):
    """Form for creating and editing Questions"""
    test_cases = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": '[{"input": "1 2", "expected_output": "3"}, {"input": "2 3", "expected_output": "5"}]',
        }),
        help_text="Enter test cases in JSON format (e.g., [{'input': '1 2', 'expected_output': '3'}]).",
        required=False,  # Allow empty test cases to match model default
    )

    class Meta:
        model = Question
        fields = ['title', 'description', 'module', 'test_cases']
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "module": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_test_cases(self):
        """Validate and convert test cases from string to JSON"""
        data = self.cleaned_data.get('test_cases', '').strip()
        if not data:
            return []  # Return empty list if no input, consistent with model default

        try:
            test_cases = json.loads(data)
            # Delegate detailed validation to the model’s validator
            Question._meta.get_field('test_cases').run_validators(test_cases)
            return test_cases
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON format: {str(e)}")
        except forms.ValidationError as e:
            raise forms.ValidationError(f"Test cases validation failed: {str(e)}")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate test_cases with JSON string if editing an existing instance
        if self.instance.pk and self.instance.test_cases:
            self.initial['test_cases'] = json.dumps(self.instance.test_cases, indent=2)
        self.fields["description"].required = False