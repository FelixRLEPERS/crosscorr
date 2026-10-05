import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Имена полей unified-схемы (data/schema/unified_schema.json). Реестр
#: обязан ссылаться на те же имена, что и загрузчики/схема; прежде здесь
#: использовалось ``timestamp`` вместо ``timestamp_utc`` (находка A24).
UNIFIED_FIELDS = ["timestamp_utc", "detector_id", "detector_type", "value"]

# Типизация для метаданных источника данных
SourceMetadata = dict[str, Any]


class SourceRegistry:
    """
    Централизованный реестр всех поддерживаемых источников данных CrossCorr.
    Содержит информацию о том, как и какие данные мы ожидаем от каждого источника.
    """
    _registry: dict[str, SourceMetadata] = {}

    @classmethod
    def register_source(cls, source_name: str, metadata: SourceMetadata):
        """Регистрирует новый источник данных."""
        if source_name in cls._registry:
            print(f"WARNING: Источник '{source_name}' уже зарегистрирован. Обновляю метаданные.")
        cls._registry[source_name] = metadata

    @classmethod
    def get_all_sources(cls) -> dict[str, SourceMetadata]:
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
    """Автоматическая инициализация реестра известными источниками.

    ``base_url`` у всех источников пока не задан (``None``): реальные
    эндпоинты не определены, а прежние значения ``https://TODO...``
    выглядели как рабочие ссылки (находка A23 / V2-29).
    """
    logger.debug("Initializing CrossCorr Source Registry...")

    # 1. WSPR (Weak Signal Propagation Reporter)
    SourceRegistry.register_source(
        "WSPR",
        {
            "description": "Споты WSPR (SNR приёмника по передатчикам).",
            "expected_fields": UNIFIED_FIELDS,
            "download_script": "data/scripts/download_wspr.py",
            "parser_module": "load_wspr (data/scripts/unify_schema.py)",
            "is_critical": True,
            "base_url": None,  # реальный эндпоинт не зафиксирован
            "api_endpoint": "drupal/wsprnet/spotquery",
        }
    )

    # 2. INTERMAGNET (магнитное поле Земли)
    SourceRegistry.register_source(
        "INTERMAGNET",
        {
            "description": "Измерения магнитного поля Земли (X/Y/Z, нТ).",
            "expected_fields": UNIFIED_FIELDS,
            "download_script": "data/scripts/download_intermagnet.py",
            "parser_module": "parse_iaga2002 (data/scripts/download_intermagnet.py)",
            "is_critical": True,
            "base_url": None,  # ручная загрузка через intermagnet.org
            "api_endpoint": None,
        }
    )

    # 3. NGL (GNSS данные)
    SourceRegistry.register_source(
        "NGL",
        {
            "description": "Глобальные навигационные спутниковые данные.",
            "expected_fields": UNIFIED_FIELDS,
            "download_script": None,  # download_ngl.py отсутствует (находка A22 / V2-28)
            "parser_module": "TODO: NGLParser (не реализован)",
            "is_critical": False,
            "base_url": None,
            "api_endpoint": None,
        }
    )


# Вызов инициализации при импорте модуля. Логирование вместо print:
# import data.scripts больше не печатает в stdout (находка A25 / V2-31).
_initialize_registry()
