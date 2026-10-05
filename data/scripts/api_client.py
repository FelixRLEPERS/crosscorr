"""Заготовка HTTP-клиента к внешним источникам CrossCorr.

Статус: не используется ни одним загрузчиком и не подключён к
``SourceRegistry``. Класс оставлен как точка расширения; реальные
эндпоинты не зафиксированы (см. полe ``base_url`` в ``registry.py``).
Находка A33 / V2-70.
"""

from __future__ import annotations

import requests


class DataClient:
    """Тонкая обёртка над ``requests.Session`` с bearer-авторизацией."""

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def get(self, url: str, **kwargs):
        """GET-запрос с поднятым статусом ошибки."""
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response
