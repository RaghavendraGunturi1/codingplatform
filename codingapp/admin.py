from django.contrib import admin
from django import forms
from django.forms import formset_factory
from .models import Module, Question, Submission

# Default Test Case Values (for pre-filling)
DEFAULT_TEST_CASE_INPUT = "Enter input here"
DEFAULT_TEST_CASE_OUTPUT = "Enter expected output here"

# Custom Form for Individual Test Case
class TestCaseForm(forms.Form):
    input = forms.CharField(
        max_length=200,
        required=False,
        initial=DEFAULT_TEST_CASE_INPUT,
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}),
        help_text="Enter the input for this test case (leave blank if no input is needed)."
    )
    expected_output = forms.CharField(
        max_length=200,
        required=True,
        initial=DEFAULT_TEST_CASE_OUTPUT,
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}),
        help_text="Enter the expected output for this test case."
    )

# Create a Formset for Test Cases using formset_factory
TestCaseFormSet = formset_factory(
    TestCaseForm,
    extra=2,
    can_delete=True
)

# Custom Form for QuestionAdmin to Handle Test Cases
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['test_cases'].widget = forms.HiddenInput()
        initial_test_cases = []
        if self.instance.pk:
            try:
                initial_test_cases = self.instance.test_cases or []
                if not isinstance(initial_test_cases, list):
                    import json
                    initial_test_cases = json.loads(self.instance.test_cases) if self.instance.test_cases else []
            except (ValueError, TypeError):
                initial_test_cases = [{"input": DEFAULT_TEST_CASE_INPUT, "expected_output": DEFAULT_TEST_CASE_OUTPUT}]
        else:
            initial_test_cases = [
                {"input": DEFAULT_TEST_CASE_INPUT, "expected_output": DEFAULT_TEST_CASE_OUTPUT},
                {"input": DEFAULT_TEST_CASE_INPUT, "expected_output": DEFAULT_TEST_CASE_OUTPUT},
            ]
        prefix = self.prefix + '-test_cases' if self.prefix else f"question_form-{self.instance.pk}-test_cases" if self.instance.pk else 'test_cases'
        self.test_case_formset = TestCaseFormSet(
            data=self.data if self.is_bound else None,
            initial=[{'input': tc.get('input', DEFAULT_TEST_CASE_INPUT), 'expected_output': tc.get('expected_output', DEFAULT_TEST_CASE_OUTPUT)} for tc in initial_test_cases],
            prefix=prefix
        )
        print(f"QuestionForm initialized with prefix: {prefix}, bound: {self.test_case_formset.is_bound}, instance pk: {self.instance.pk}")  # Debug

    def is_valid(self):
        is_valid = super().is_valid()
        formset_is_valid = self.test_case_formset.is_valid()
        print(f"Form valid: {is_valid}, Formset valid: {formset_is_valid}, Formset errors: {self.test_case_formset.errors}")  # Debug
        return is_valid and formset_is_valid

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.test_case_formset.is_valid():
            test_cases_data = [
                {"input": form.cleaned_data.get('input', ''), "expected_output": form.cleaned_data['expected_output']}
                for form in self.test_case_formset.forms
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
            ]
            instance.test_cases = test_cases_data
            print(f"Saved test cases to database: {test_cases_data}")  # Debug
        if commit:
            instance.save()
        return instance

# Inline Admin for Questions within ModuleAdmin
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    readonly_fields = ('module',)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(f"QuestionInline get_context_data called, context: {context.get('inline_admin_formset')}, forms count: {len(context['inline_admin_formset'].forms)}")  # Debug
        return context

# Custom Admin for Module with Question Inline
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    change_form_template = 'admin/codingapp/module/change_form.html'
    list_display = ('title',)
    search_fields = ('title',)
    list_filter = ()
    inlines = [QuestionInline]

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        print(f"ModuleAdmin get_inline_instances called, inlines: {[type(inline) for inline in inlines]}")  # Debug
        return inlines

    def change_view(self, request, object_id, form_url='', extra_context=None):
        print(f"ModuleAdmin change_view called with object_id: {object_id}")  # Debug
        extra_context = extra_context or {}
        response = super().change_view(request, object_id, form_url, extra_context)
        print(f"ModuleAdmin change_view context inline_admin_formsets: {len(extra_context.get('inline_admin_formsets', []))}")  # Debug
        return response

# Custom Admin for Question (standalone)
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm
    change_form_template = 'admin/codingapp/question/change_form.html'
    list_display = ('title', 'module')
    search_fields = ('title',)
    list_filter = ('module',)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            form_class = self.form
            if request.method == 'POST':
                form = form_class(request.POST, instance=obj, prefix=f'question_form-{object_id}')
                if form.is_valid():
                    form.save()
            else:
                form = form_class(instance=obj, prefix=f'question_form-{object_id}')
            if hasattr(form, 'test_case_formset'):
                extra_context['test_case_formset'] = form.test_case_formset
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        form = self.form()
        if hasattr(form, 'test_case_formset'):
            extra_context['test_case_formset'] = form.test_case_formset
        return super().add_view(request, form_url, extra_context=extra_context)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'status', 'submitted_at')
    search_fields = ('user__username', 'question__title')
    list_filter = ('status', 'language', 'submitted_at')