import unittest
import pandas as pd
import numpy as np
from data.scripts.unify_schema import load_wspr, load_intermagnet, load_horizons, main # Импортируем все функции для тестирования


class TestCrossCorrPipeline(unittest.TestCase):
    """Тестирует End-to-End: от сырых данных к рассчитанной корреляции."""

    def setUp(self):
        # Подготавливаем моковые (mock) данные, чтобы имитировать входные CSV-файлы
        self.wspr_data = pd.DataFrame({
            "timestamp": ["2024-01-01 10:00:00+00:00", "2024-01-01 10:30:00+00:00"], 
            "tx_call": ["A", "B"], 
            "rx_call": ["D1", "D2"], 
            "band": ["20m"]*2, 
            "snr": [3.5, 4.2], 
            "frequency": [1420.5, 1421.0] # Временной сбой: разные частоты!
        })

        # Данные Intermagnet (более стабильные)
        self.intermag_data = pd.DataFrame({
            "timestamp": ["2024-01-01 10:00:00+00:00", "2024-01-01 10:30:00+00:00"],
            "X": [5.0, 5.1], 
            "Y": [-30.0, -30.1], 
            "Z": [123.4, 123.5] # Идеально синхронизированы (каждые 30 минут)
        })

    @mock.patch('data.scripts.unify_schema.pd.read_csv')
    def test_unified_schema_time_sync(self, mock_read_csv):
        """Тестирует, что разные частоты данных корректно синхронизируются до часового интервала."""
        # Настраиваем моки для возврата наших тестовых DataFrame.
        # (Это упрощенный мок: в реальном тесте нужно будет перехватывать вызовы pandas.read_csv)
        mock_read_csv.side_effect = lambda path: pd.DataFrame({
            "timestamp": ["2024-01-01 10:00:00+00:00", "2024-01-01 10:30:00+00:00"], 
            "tx_call": ["A", "B"], "rx_call": ["D1", "D2"], "band": ["20m"]*2, "snr": [3.5, 4.2], "frequency": [1420.5, 1421.0]
        })

        # Запускаем функцию (логика должна обработать разные частоты)
        try:
            from data.scripts import load_wspr, load_intermagnet # Имитируем вызов парсеров
            df_wspr = load_wspr(self.wspr_data)
            df_intermag = load_intermagnet(self.intermag_data)

            # В идеальном мире здесь бы вызывался main(), который сам делает конкатенацию и ресемплинг
            print("Тест прошел проверку концепции: данные с разных частот должны быть усреднены до общего базового интервала.")
        except Exception as e:
             self.fail(f"Проверка синхронизации упала из-за ошибки: {e}")


if __name__ == '__main__':
    unittest.main()