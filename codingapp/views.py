import requests
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from .models import Question, Submission, Module
from .forms import ModuleForm, QuestionForm
from django.contrib import messages

# Piston API Configuration
PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

# Supported Languages (simplified since Piston uses these directly)
SUPPORTED_LANGUAGES = ["python", "c", "cpp", "java", "javascript"]

# Logger for debugging
logger = logging.getLogger(__name__)

# Admin check function
def is_admin(user):
    return user.is_staff

# Helper function to execute code via Piston API
def execute_code(code, language, test_cases):
    results = []
    error_output = None

    for test in test_cases or []:
        test_input = test.get("input", "")
        expected_output = test.get("expected_output", "")

        submission_data = {
            "language": language,
            "version": "*",
            "files": [{"name": "solution", "content": code}],
            "stdin": test_input
        }

        try:
            response = requests.post(PISTON_API_URL, json=submission_data, timeout=10)
            response.raise_for_status()
            result_data = response.json()

            actual_output = result_data.get("run", {}).get("stdout", "").strip()
            error_output = result_data.get("run", {}).get("stderr", "").strip()

            status = "Accepted" if actual_output == expected_output else "Rejected" if not error_output else "Error"
            results.append({
                "input": test_input,
                "expected_output": expected_output,
                "actual_output": actual_output,
                "status": status,
                "error_message": error_output if status == "Error" else ""
            })
        except requests.exceptions.RequestException as e:
            error_output = f"API error: {e}"
            results.append({
                "input": test_input,
                "expected_output": expected_output,
                "actual_output": "",
                "status": "Error",
                "error_message": error_output
            })
            break

    return results, error_output

# Module-related views
def module_list(request):
    modules = Module.objects.all()
    return render(request, 'codingapp/module_list.html', {'modules': modules})

def module_detail(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    questions = module.questions.all()  # Fetch questions explicitly
    return render(request, 'codingapp/module_detail.html', {'module': module, 'questions': questions})

@staff_member_required
def add_module(request):
    if request.method == "POST":
        form = ModuleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("module_list")
    else:
        form = ModuleForm()
    return render(request, "codingapp/module_form.html", {"form": form})

@staff_member_required
def edit_module(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if request.method == "POST":
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            return redirect("module_list")
    else:
        form = ModuleForm(instance=module)
    return render(request, "codingapp/module_form.html", {"form": form})

@staff_member_required
def delete_module(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if request.method == "POST":
        module.delete()
        return redirect("module_list")
    return render(request, "codingapp/module_confirm_delete.html", {"module": module})

# Question-related views
@login_required
@user_passes_test(is_admin)
def add_question_to_module(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.module = module
            question.save()
            return redirect('module_detail', module_id=module.id)
    else:
        form = QuestionForm()
    return render(request, 'codingapp/add_question.html', {'form': form, 'module': module})

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

@login_required
def user_dashboard(request):
    user_submissions = Submission.objects.filter(user=request.user).order_by('-submitted_at')
    return render(request, 'codingapp/dashboard.html', {'user_submissions': user_submissions})

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'codingapp/register.html', {'form': form})

def question_list(request):
    questions = Question.objects.all()
    return render(request, 'codingapp/question_list.html', {'questions': questions})

@login_required
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)
    code = request.session.get(f'code_{pk}', '')
    selected_language = request.session.get(f'language_{pk}', 'python')

    # Fallback to last submission if no session data
    if not code and request.user.is_authenticated:
        last_submission = Submission.objects.filter(user=request.user, question=question).order_by('-submitted_at').first()
        if last_submission:
            code = last_submission.code or ""
            selected_language = last_submission.language or "python"

    error = None  # Always initialize error
    error_output = None  # Always initialize error_output
    results = None  # Always initialize results

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        selected_language = request.POST.get("language", "python")

        if selected_language not in SUPPORTED_LANGUAGES:
            selected_language = "python"  # Fallback to default

        if not code:
            error = "Code cannot be empty"
        else:
            # Save to session
            request.session[f'code_{pk}'] = code
            request.session[f'language_{pk}'] = selected_language
            request.session.modified = True

            # Execute code and get results
            results, error_output = execute_code(code, selected_language, question.test_cases)
            if error_output:
                error = "Error executing code"
            
            # Save submission
            submission = Submission.objects.create(
                question=question,
                user=request.user,
                code=code,
                language=selected_language,
                status=results[0]["status"] if results and results[0]["status"] else "Pending",
                output=results[0]["actual_output"] if results and results[0]["actual_output"] else "",
                error=error_output or ""
            )
            messages.success(request, "Code submitted successfully!") if not error else messages.error(request, error)

    return render(request, "codingapp/question_detail.html", {
        "question": question,
        "code": code,
        "selected_language": selected_language,
        "results": results,
        "error": error,  # Always included
        "error_output": error_output,  # Always included
    })

@login_required
def submit_solution(request, pk):
    question = get_object_or_404(Question, pk=pk)
    code = request.session.get(f'code_{pk}', '')
    selected_language = request.session.get(f'language_{pk}', 'python')

    error = None  # Always initialize error
    error_output = None  # Always initialize error_output
    results = None  # Always initialize results

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        selected_language = request.POST.get("language", "python")

        if selected_language not in SUPPORTED_LANGUAGES:
            selected_language = "python"

        if not code:
            error = "Code cannot be empty"
        else:
            # Save submission
            submission = Submission.objects.create(
                question=question,
                user=request.user,
                code=code,
                language=selected_language
            )
            results, error_output = execute_code(code, selected_language, question.test_cases)
            submission.status = "Accepted" if all(r["status"] == "Accepted" for r in results) else "Rejected" if results else "Pending"
            submission.output = results[0]["actual_output"] if results and results[0]["actual_output"] else ""
            submission.error = error_output or ""
            submission.save()

            # Update session
            request.session[f'code_{pk}'] = code
            request.session[f'language_{pk}'] = selected_language
            request.session.modified = True

            if error_output:
                error = "Error executing code"
                messages.error(request, error)
            else:
                messages.success(request, "Code submitted successfully!")

    return render(request, "codingapp/question_detail.html", {
        "question": question,
        "code": code,
        "selected_language": selected_language,
        "results": results,
        "error": error,  # Always included
        "error_output": error_output,  # Always included
    })