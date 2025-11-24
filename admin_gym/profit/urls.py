from django.urls import path, include
from admin_gym import views

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('', include('admin_gym.urls')),
]