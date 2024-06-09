from django.urls import path # функция для определения URL-маршрутов
from main import views # модуль, где определены функции представлений

# определение маршрутизации в django
urlpatterns = [
    path('', views.index, name='index'),
    path('decode_audio/', views.decode_audio, name='decode_audio'),
    path('download_encoded_audio/', views.download_encoded_audio, name='download_encoded_audio'),
]