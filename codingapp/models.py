from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import slugify  # Imported here for slug generation

def validate_test_cases(value):
    """Validate that test_cases is a list of dictionaries with 'input' and 'expected_output'."""
    if not isinstance(value, list):
        raise ValidationError("Test cases must be a list.")
    for test in value:
        if not isinstance(test, dict) or "input" not in test or "expected_output" not in test:
            raise ValidationError("Each test case must be a dict with 'input' and 'expected_output' keys.")

class Module(models.Model):
    """Model representing a module with questions."""
    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """Generate slug from title if not set."""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']

class Question(models.Model):
    """Model representing a coding question with test cases."""
    title = models.CharField(max_length=200)
    description = models.TextField()
    module = models.ForeignKey(
        Module, 
        on_delete=models.CASCADE, 
        related_name="questions", 
        null=True, 
        blank=True
    )
    test_cases = models.JSONField(
        default=list, 
        validators=[validate_test_cases],
        help_text="Managed via admin formset; do not edit manually."
    )


    def __str__(self):
        return self.title

    class Meta:
        unique_together = ['module', 'title']

# Define choices statically
SUPPORTED_LANGUAGES = ["python", "c", "cpp", "java", "javascript"]
LANGUAGE_CHOICES = [(lang, lang.capitalize()) for lang in SUPPORTED_LANGUAGES]

class Submission(models.Model):
    """Model representing a user's code submission."""
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        ACCEPTED = "Accepted", "Accepted"
        REJECTED = "Rejected", "Rejected"

    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.TextField(blank=True)
    language = models.CharField(
        max_length=50, 
        choices=LANGUAGE_CHOICES, 
        default="python"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    output = models.TextField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.title} ({self.submitted_at})"

    class Meta:
        ordering = ['-submitted_at']  # Added for consistency with admin sorting