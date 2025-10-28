from django.urls import path
from . import views


app_name = 'main'

urlpatterns = [
    path('', views.recipe_form_view, name='recipe_form'),
    path('upload/', views.upload_view, name='upload'),
    path('files/', views.files_list_view, name='files_list'),
    path('files/<str:kind>/<str:filename>/', views.file_detail_view, name='file_detail'),
    
    # Новые URL для работы с БД
    path('data-source/', views.data_source_choice_view, name='data_source_choice'),
    path('database/', views.database_recipes_view, name='database_recipes'),
    path('ajax/search/', views.ajax_search_recipes, name='ajax_search'),
    path('recipes/<int:recipe_id>/', views.recipe_detail_view, name='recipe_detail'),
    path('recipes/<int:recipe_id>/edit/', views.recipe_edit_view, name='recipe_edit'),
    path('recipes/<int:recipe_id>/delete/', views.recipe_delete_view, name='recipe_delete'),
]


