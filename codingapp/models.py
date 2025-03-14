from django.db import models

class Module(models.Model):
    title = models.CharField(max_length=255, unique=True)  # Ensuring uniqueness
    description = models.TextField(blank=True, null=True)  # Keeping optional description
    created_at = models.DateTimeField(auto_now_add=True)  # Keeping created_at field

    def __str__(self):
        return self.title


class Question(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    test_cases = models.JSONField(default=list)  # Ensure test case format consistency

    def __str__(self):
        return self.title


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        ACCEPTED = "Accepted", "Accepted"
        REJECTED = "Rejected", "Rejected"

    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user_name = models.CharField(max_length=255)  # Can be replaced with a User ForeignKey later
    code = models.TextField(blank=True)  # Stores user's submitted code
    language = models.CharField(max_length=50)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    output = models.TextField(blank=True, null=True)  # Stores execution output
    error = models.TextField(blank=True, null=True)  # Stores execution errors

    def __str__(self):
        return f"{self.user_name} - {self.question.title} ({self.submitted_at})"
