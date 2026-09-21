import unittest
from unittest import mock
import pandas as pd
import datetime as dt
import requests
from data.scripts.download_wspr import fetch_wspr

# Фикстура для имитации объекта DataFrame при тестах
class MockDataFrame(pd.DataFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
def test_fetch_wspr_success(mock_get):
    """Тестирует успешный сценарий: API возвращает данные без ошибок."""
    # Настраиваем мок для имитации 200 OK ответа
    mock_response = unittest.mock.Mock()
    mock_response.raise_for_status.return_value = None # Успешное завершение
    mock_response.text = "timestamp,tx_call,rx_call,band,snr,frequency\n2024-01-01T00:00:00Z,D1,D2,20m,3.5,1420.5"
    mock_get.return_value = mock_response

    # Выполняем функцию с мок'ом requests.get
    result_df = fetch_wspr(dt.date.today(), "20m", 1)

    assert not result_df.empty, "DataFrame должен быть заполнен после успешного запроса."
    assert len(result_df) == 1, "Должна быть получена ровно одна строка тестовых данных."


@mock.patch('data.scripts.fetch_wspr')
def test_fetch_wspr_network_failure_retry(mock_fetch):
    """Тестирует логику повторных попыток при временном сетевом сбое."""
    # 1. Настройка мока: Первая ошибка - ConnectionError, вторая - Timeout, третья - Успех.
    mock_fetch.side_effect = [
        requests.exceptions.ConnectionError("Network unstable"), # Попытка 1: Сбой сети
        requests.exceptions.Timeout("API timed out"),           # Попытка 2: Таймаут
        pd.DataFrame({"timestamp": ["2024-01-03T00:00:00Z"], "tx_call": ["D3"]}) # Успех на третьей попытке
    ]

    # Вызываем функцию - она должна успешно завершиться благодаря retries.
    result_df = fetch_wspr(dt.date.today(), "20m", 1)
    
    assert not result_df.empty, "Функция должна вернуть данные после нескольких попыток."


@mock.patch('data.scripts.fetch_wspr')
def test_fetch_wspr_permanent_failure(mock_fetch):
    """Тестирует сценарий: API постоянно возвращает ошибку 403 Forbidden."""
    # Настраиваем мок, который всегда вызывает HTTPError (например, из-за неверного ключа)
    mock_response = unittest.mock.Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")
    mock_get = mock.Mock(return_value=mock_response)
    
    # Принудительно внедряем мок для проверки (в реальном тесте это было бы в setup/fixture)
    with mock.patch('requests.get', return_value=mock_get):
        result_df = fetch_wspr(dt.date.today(), "20m", 1)
        assert result_df is None, "Должен вернуть None при постоянной ошибке API."