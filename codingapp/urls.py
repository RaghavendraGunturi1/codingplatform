from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Core Routes
    path('', views.home, name='home'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    path('questions/', views.question_list, name='question_list'),
    path('questions/<int:pk>/', views.question_detail, name='question_detail'),  # Fixed to map to question_detail

    # Authentication Routes
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Module Routes
    path('modules/', views.module_list, name='module_list'),
    path('modules/<int:module_id>/', views.module_detail, name='module_detail'),
    path('modules/add/', views.add_module, name='add_module'),
    path('modules/<int:module_id>/edit/', views.edit_module, name='edit_module'),
    path('modules/<int:module_id>/delete/', views.delete_module, name='delete_module'),
    path('modules/<int:module_id>/add-question/', views.add_question_to_module, name='add_question'),
]