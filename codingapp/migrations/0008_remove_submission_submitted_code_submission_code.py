# Generated by Django 5.1.6 on 2025-03-13 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('codingapp', '0007_remove_submission_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='submission',
            name='submitted_code',
        ),
        migrations.AddField(
            model_name='submission',
            name='code',
            field=models.TextField(blank=True),
        ),
    ]
