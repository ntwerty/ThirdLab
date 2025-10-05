from django.urls import path
from . import views


app_name = 'main'

urlpatterns = [
    path('', views.recipe_form_view, name='recipe_form'),
    path('upload/', views.upload_view, name='upload'),
    path('files/', views.files_list_view, name='files_list'),
    path('files/<str:kind>/<str:filename>/', views.file_detail_view, name='file_detail'),
]


