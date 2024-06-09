# импорт базового модуля для конфигурации приложения
from django.apps import AppConfig
# конфигурация приложения
class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
