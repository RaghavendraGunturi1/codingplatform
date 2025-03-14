import requests
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import JsonResponse
from .models import Question, Submission, Module
from .forms import ModuleForm, QuestionForm
from django.contrib import messages

# ✅ Piston API Configuration for Code Execution
PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

# ✅ Supported Languages Mapping (For Piston API)
SUPPORTED_LANGUAGES = {
    "python": "python",
    "c": "c",
    "cpp": "cpp",
    "java": "java",
    "javascript": "javascript"
}

# ✅ Admin check function
def is_admin(user):
    return user.is_staff

# ✅ Module-related views
def module_list(request):
    modules = Module.objects.all()
    return render(request, 'codingapp/module_list.html', {'modules': modules})

def module_detail(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    return render(request, 'codingapp/module_detail.html', {'module': module})

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

# ✅ Question-related views
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
    user_submissions = Submission.objects.filter(user_name=request.user.username).order_by('-submitted_at')
    return render(request, 'codingapp/dashboard.html', {'user_submissions': user_submissions})

def register(request):
    """ User Registration """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'codingapp/register.html', {'form': form})

def question_list(request):
    """ Lists all coding questions """
    questions = Question.objects.all()
    return render(request, 'codingapp/question_list.html', {'questions': questions})

from django.shortcuts import render, get_object_or_404
from .models import Question, Submission
import requests

PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"  # Ensure this is correct

def question_detail(request, pk):
    """ Show a single question with session-based code persistence """
    question = get_object_or_404(Question, pk=pk)
    results = []  # Store test case results
    error_output = None  # Store errors

    # Retrieve stored code and language from session
    code = request.session.get(f'code_{pk}', '')  
    selected_language = request.session.get(f'language_{pk}', 'python')


    # ✅ Default values for first-time users
    code = request.session.get('last_code', "")  # Retrieve from session if available
    selected_language = request.session.get('selected_language', "python")  # Default Python

    # ✅ If user is authenticated, get their last submission from DB (if session is empty)
    if request.user.is_authenticated and not code:
        last_submission = Submission.objects.filter(
            user_name=request.user.username, question=question
        ).order_by('-submitted_at').first()

        if last_submission:
            code = last_submission.code or ""
            selected_language = last_submission.language or "python"
     

    # ✅ If request method is POST, process the submitted code
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        selected_language = request.POST.get("language", "python")

        # ✅ Store the last submitted code and language in session
        request.session[f'code_{pk}'] = code
        request.session[f'language_{pk}'] = selected_language
        request.session.modified = True  # Ensure session updates are saved

        # DEBUGGING: Print stored session data in console
        print(f"Saved Code for Q{pk}: {request.session.get(f'code_{pk}', '')}")
        print(f"Saved Language for Q{pk}: {request.session.get(f'language_{pk}', 'python')}")


        if not code:
            return render(request, "codingapp/question_detail.html", {
                "question": question,
                "code": code,  # Keep last valid code
                "selected_language": selected_language,
                "error": "Code cannot be empty"
            })

        # ✅ Store submitted code in session
        request.session['last_code'] = code
        request.session['selected_language'] = selected_language

        # ✅ Save the submission in DB
        submission = Submission.objects.create(
            question=question,
            user_name=request.user.username,
            code=code,
            language=selected_language
        )

        test_cases = question.test_cases or []  # Ensure test_cases is always a list

        for test in test_cases:
            test_input = test.get("input", "")
            expected_output = test.get("expected_output", "")

            # ✅ Construct API request for code execution
            submission_data = {
                "language": selected_language,
                "version": "*",
                "files": [{"name": "solution", "content": code}],
                "stdin": test_input
            }

            try:
                response = requests.post(PISTON_API_URL, json=submission_data)
                response.raise_for_status()  # Raise error for non-200 responses

                result_data = response.json()

                # ✅ Extract execution output and errors
                actual_output = result_data.get("run", {}).get("stdout", "").strip()
                error_output = result_data.get("run", {}).get("stderr", "").strip()

                if error_output:
                    submission.status = "Rejected"
                    submission.output = "Error Occurred"
                    submission.error = error_output
                    submission.save()

                    return render(request, "codingapp/question_detail.html", {
                        "question": question,
                        "code": code,  # Preserve code
                        "selected_language": selected_language,
                        "error_output": error_output
                    })

                # ✅ Check if output matches expected result
                status = "Accepted" if actual_output == expected_output else "Rejected"
                submission.status = status
                submission.output = actual_output
                submission.error = error_output
                submission.save()

                # Append test case results
                results.append({
                    "input": test_input,
                    "expected_output": expected_output,
                    "actual_output": actual_output,
                    "status": status
                })

            except requests.exceptions.RequestException as e:
                error_output = f"API error occurred: {e}"
                submission.status = "Rejected"
                submission.error = error_output
                submission.save()

        return render(request, "codingapp/question_detail.html", {
            "question": question,
            "code": code,  # Pass last submitted code
            "selected_language": selected_language,
            "results": results,
            "error_output": error_output
        })

    # ✅ Render the question detail page for GET requests
    return render(request, "codingapp/question_detail.html", {
        "question": question,
        "code": code,  # Preload last submitted code (from session or DB)
        "selected_language": selected_language
    })
@login_required
def submit_solution(request, pk):
    """Handles code submission using Piston API, saves last submitted code, and executes test cases."""
    print("✅ Debug: submit_solution() function triggered!")  
    question = get_object_or_404(Question, pk=pk)
    # Ensure 'code' always has a default value
    code = request.session.get("last_code", "")
    selected_language = request.session.get("selected_language", "python")

    if request.method == "POST":
        code = request.POST.get("code", "")  # Retrieve submitted code
        selected_language = request.POST.get("language", "python")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        language = request.POST.get("language", "python")  # Default language
        selected_language = SUPPORTED_LANGUAGES.get(language, "python")  # Ensure correct API mapping
        print("✅ Submitted Code:", code)# Debugging line 
        if not code:
            return render(request, "codingapp/question_detail.html", {
                "question": question,
                "code": code,
                "error": "Code cannot be empty."
            })

        # ✅ Save last submitted code in database
        Submission.objects.create(
            question=question,
            user_name=request.user.username,
            code=code,  # ✅ Changed to use `code`
            language=selected_language,
            
        )

        test_cases = question.test_cases  # Fetch test cases from DB
        results = []
        error_output = None  # Initialize error message

        for test in test_cases:
            test_input = test["input"]
            expected_output = test["expected_output"]

            # ✅ Construct Piston API request
            submission_data = {
                "language": selected_language,
                "version": "*",
                "files": [{"name": "solution", "content": code}],
                "stdin": test_input
            }

            try:
                response = requests.post(PISTON_API_URL, json=submission_data)
                if response.status_code != 200:
                    return render(request, "codingapp/question_detail.html", {
                        "question": question,
                        "code": code,
                        "error": "Failed to submit code. Try again."
                    })

                result_data = response.json()
                print("✅ API Response:", result_data)  # Debugging line
                
                # ✅ Fix: Ensure .strip() is not called on None
                actual_output = result_data["run"].get("stdout", "").strip()
                error_output = result_data["run"].get("stderr", "").strip()

                # If there's an error, display it instead of actual output
                if error_output:
                    actual_output = "Error Occurred"
                    status = "Error"
                else:
                    status = "Accepted" if actual_output == expected_output else "Rejected"

                # Append results
                results.append({
                    "input": test_input,
                    "expected_output": expected_output,
                    "actual_output": actual_output,
                    "status": status,
                    "error_message": error_output  # Send error to template
                })

            except requests.exceptions.RequestException as e:
                error_output = f"API error occurred: {e}"

        return render(request, "codingapp/question_detail.html", {
            "question": question,
            "code": code,  # ✅ Pass last submitted code to template
            "results": results,
            "error_output": error_output
        })
    # DEBUGGING: Print session data when returning to the page
    print(f"Returning Code for Q{pk}: {code}")

    return render(request, "codingapp/question_detail.html", {
        "question": question,
        "code": "code",
        "error": "Invalid request"
        
    })
    