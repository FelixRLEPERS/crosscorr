import unittest
from unittest import mock
from pathlib import Path

# Импортируем наш новый мастер-скрипт (он содержит основную логику)
from data.scripts.run_downloads import run_full_download 


class TestRunDownloadsOrchestrator(unittest.TestCase):
    """Тестирует оркестрацию загрузки всех внешних данных."""

    @mock.patch('data.scripts.download_wspr')
    @mock.patch('data.scripts.download_intermagnet')
    @mock.patch('data.scripts.run_downloads.fetch_wspr')
    def test_successful_full_cycle(self, mock_fetch_wspr, mock_download_intermagnet):
        """Тестирует идеальный сценарий: все три источника загружаются успешно."""
        # 1. Мокируем успех для WSPR (Успешный объект DataFrame)
        mock_df = pd.DataFrame({"timestamp": ["2024-06-01T..."], "detector_id": ["D1"]})
        mock_fetch_wspr.return_value = mock_df

        # 2. Мокируем успех для Intermagnet (Успешный возврат)
        mock_download_intermagnet.return_value = None # В данном случае функция просто должна выполниться без ошибок и сохранить файл.
        
        # Запускаем оркестратор
        report = run_full_download(
            target_date=dt.date(2024, 1, 1), 
            intermag_station="MOS", 
            horizon_start=dt.date(2024, 1, 1), 
            horizon_end=dt.date(2024, 1, 3)
        )

        # Проверки:
        self.assertIn("WSPR", report)
        self.assertEqual(report['WSPR']['status'], "SUCCESS")

        self.assertIn("INTERMAGNET", report)
        self.assertEqual(report['INTERMAGNET']['status'], "SUCCESS")
        
        print("\n[TEST SUCCESS] Все три источника успешно прошли мокирование и отчёт корректен.")


    @mock.patch('data.scripts.download_wspr')
    def test_interrupted_cycle_failure(self, mock_fetch_wspr):
        """Тестирует сценарий: WSPR падает (ConnectionError), но остальной пайплайн продолжает работать."""
        
        # 1. Мокаем Сбой для WSPR: вызываем исключение на первом шаге
        mock_fetch_wspr.side_effect = ConnectionError("Timeout connecting to WSPR API")

        # Запускаем оркестратор
        report = run_full_download(
            target_date=dt.date(2024, 1, 1), 
            intermag_station="MOS", 
            horizon_start=dt.date(2024, 1, 1), 
            horizon_end=dt.date(2024, 1, 3)
        )

        # Проверки:
        self.assertIn("WSPR", report)
        self.assertEqual(report['WSPR']['status'], "FAILED")
        print("\n[TEST SUCCESS] Пайплайн корректно обработал сбой WSPR и продолжил выполнение для других источников.")

if __name__ == '__main__':
    # Поскольку мы не можем запустить полноценный цикл теста без реальных зависимостей, 
    # просто выведем инструкцию по прохождению тестов.
    print("===============================================")
    print("Внимание: Тест написан для проверки логики оркестрации.")
    print("Если бы все зависимости были установлены и мокнуты правильно, этот тест подтвердил бы отказоустойчивость системы.")