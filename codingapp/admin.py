from django.contrib import admin
from django import forms
from .models import Module, Question, Submission

# ✅ Default Test Case Format
DEFAULT_TEST_CASES = [
    {"input": "Enter_input_here", "expected_output": "Enter_expected_output_here"},
    {"input": "Enter_input_here", "expected_output": "Enter_expected_output_here"},
]


# ✅ Custom Form for QuestionAdmin to Pre-fill Test Cases
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:  # Only apply to new questions
            self.fields['test_cases'].initial = DEFAULT_TEST_CASES


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm  # ✅ Attach the custom form
    list_display = ('title', 'module')
    search_fields = ('title',)
    list_filter = ('module',)


admin.site.register(Submission)  # Keeping Submission registration unchanged
