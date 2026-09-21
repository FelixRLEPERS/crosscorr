import unittest
import os
from data.scripts import SourceRegistry # Импорт нашего реестра

class TestSourceRegistry(unittest.TestCase):
    """Тестирует правильную инициализацию и валидацию источников данных."""

    def setUp(self):
        # Очистка или подготовка окружения перед каждым тестом (если потребуется)
        pass

    def test_registry_initialization(self):
        """Проверяет, что все основные источники были автоматически зарегистрированы при импорте."""
        all_sources = SourceRegistry.get_all_sources()
        print("\n--- Тест: Проверка регистрации источников ---")
        
        # Ожидаем как минимум 3 основных источника
        self.assertGreaterEqual(len(all_sources), 3, f"Ожидалось минимум 3 источника, найдено только {len(all_sources)}.")

    def test_source_existence(self):
        """Проверяет существование известных источников."""
        # Проверяем конкретных критически важных источники
        self.assertTrue("WSPR" in SourceRegistry.get_all_sources(), "WSPR не найден в реестре.")
        self.assertTrue("NGL" in SourceRegistry.get_all_sources(), "NGL не найден в реестре.")

    @unittest.mock.patch('data.scripts.api_client.DataClient')
    def test_fetch_unknown_source(self, MockDataClient):
        """Проверяет отказ при запросе неизвестного источника (SourceRegistry должен это поймать)."""
        # Создаем заглушку для API клиента, чтобы протестировать метод fetch_data_by_source
        client = DataClient("test_key") 
        result = client.fetch_data_by_source("NON_EXISTENT_SOURCE", **{})
        self.assertIsNone(result)

    @unittest.mock.patch('requests.Session')
    def test_successful_api_call_validation(self, MockSession):
        """Проверяет успешный путь: от реестра -> API запрос -> Парсинг."""
        # 1. Настраиваем моки для имитации успешного запроса (Success Path Simulation)
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [{"timestamp": "2024-01-01T00:00:00Z", "detector_id": "A", "residual": 1.5}]
        }
        mock_session_instance = unittest.mock.Mock()
        mock_session_instance.get.return_value = mock_response

        # Обновляем клиента для теста с моком
        client = DataClient("test_key")
        client.session = mock_session_instance # Внедряем наш Mock-объект сессии
        
        # 2. Выполняем действие: Запрос к известному источнику
        result = client.fetch_data_by_source("WSPR", **{})

        self.assertIsNotNone(result)
        # Проверка, что клиент действительно использовал данные WSPR для трансформирования
        self.assertEqual(result['source'], "WSPR")
        self.assertTrue('record_count' in result)
        """Проверяет, что запрос неизвестного источника возвращает False."""
        self.assertFalse(SourceRegistry.is_registered("NON_EXISTENT_SOURCE"), "Должно быть невозможно зарегистрировать несуществующий источник.")

# Если бы у нас был реальный класс DataClient, мы бы добавили:
# class TestDataClient(unittest.TestCase):
#     def test_fetch_unknown_source(self):
#         client = DataClient("test_key") # Заглушка для API ключа
#         result = client.fetch_data_by_source("BAD_SOURCE", **{})
#         self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()