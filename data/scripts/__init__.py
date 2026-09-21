from .registry import SourceRegistry

# Инициализируем реестр при импорте всего пакета data.scripts
SourceRegistry # Вызов класса гарантирует запуск _initialize_registry() в registry.py