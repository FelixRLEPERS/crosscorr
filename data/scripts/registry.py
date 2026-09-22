from typing import Dict, List, Any, Optional
import re  # импортируем для потенциальной обработки Regex в будущем


# Типизация для метаданных источника данных
SourceMetadata = Dict[str, Any]


class SourceRegistry:
    """
    Централизованный реестр всех поддерживаемых источников данных CrossCorr.
    Содержит информацию о том, как и какие данные мы ожидаем от каждого источника.
    """
    _registry: Dict[str, SourceMetadata] = {}

    @classmethod
    def register_source(cls, source_name: str, metadata: SourceMetadata):
        """Регистрирует новый источник данных."""
        if source_name in cls._registry:
            print(f"WARNING: Источник '{source_name}' уже зарегистрирован. Обновляю метаданные.")
        cls._registry[source_name] = metadata

    @classmethod
    def get_all_sources(cls) -> Dict[str, SourceMetadata]:
        """Возвращает все зарегистрированные источники."""
        return cls._registry

    @classmethod
    def is_registered(cls, source_name: str) -> bool:
        """Проверяет, известен ли источник данных."""
        return source_name in cls._registry


# ==============================================
# Инициализация и регистрация известных источников
# Эта секция должна быть расширена при добавлении новых источников.
# ==============================================

def _initialize_registry():
    """Автоматическая инициализация реестра известными источниками."""
    print("Initializing CrossCorr Source Registry...")

    # 1. WSPR (Worldwide Survey of Pulsars and Radio sources)
    SourceRegistry.register_source(
        "WSPR",
        {
            "description": "Данные о радиосигналах от источников пульсаров.",
            "expected_fields": ["timestamp", "detector_id", "residual"],
            "download_script": "data/scripts/download_wspr.py",
            "parser_module": "WSPRParser",
            "is_critical": True,
            "base_url": "https://api.crosscorr.org/v1/",
            "api_endpoint": "sources/wspr",
        }
    )

    # 2. INTERMAGNET (Магнитное поле Земли)
    SourceRegistry.register_source(
        "INTERMAGNET",
        {
            "description": "Измерения магнитного поля Earth's field.",
            "expected_fields": ["timestamp", "detector_id", "field_strength"],
            "download_script": "data/scripts/download_intermagnet.py",
            "parser_module": "InterMagnetParser",
            "is_critical": True,
            "base_url": "https://api.crosscorr.org/v1/",
            "api_endpoint": "sources/intermagnet",
        }
    )

    # 3. NGL (GNSS данные)
    SourceRegistry.register_source(
        "NGL",
        {
            "description": "Глобальные навигационные спутниковые данные.",
            "expected_fields": ["timestamp", "detector_id", "latitude"],
            "download_script": "data/scripts/download_ngl.py",
            "parser_module": "NGLParser",
            "is_critical": False,
            "base_url": "https://api.crosscorr.org/v1/",
            "api_endpoint": "sources/ngl",
        }
    )


# Вызов инициализации при импорте модуля
_initialize_registry()