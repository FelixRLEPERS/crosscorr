import unittest
from unittest import mock
from data.scripts.api_client import DataClient # Используем для имитации доступа к структуре API
# Импортируем наш модуль, который мы только что написали
from code.ai_narrator import AINarrator 

class TestAINarrator(unittest.TestCase):
    """Тестирует логику генерации повествования и оркестровку AI-наставника."""

    def setUp(self):
        # Инициализация нашего класс-оркестратора
        self.narrator = AINarrator()

    @mock.patch('pandas.read_csv')
    def test_scenario_success_found_pair(self, mock_pd_read_csv):
        """Тест успешного сценария: находим 2 или более значимых связей."""
        # 1. Создаем мок-данные для симуляции успешной загрузки CSV (порядок важен!)
        mock_df = pd.DataFrame({
            'Detector1': ['WSPR', 'INTERMAGNET'],
            'Detector2': ['A', 'B'],
            'Correlation_Strength(r)': [0.75, 0.9],
            'P_Value': [0.01, 0.001],
            'FDR_Adjusted_P': [0.01, 0.001], # Эти значения говорят о значимости
            'Significant_Pair': ['True', 'True']
        })
        mock_pd_read_csv.return_value = mock_df

        # Запускаем анализ (логика должна извлечь обе пары)
        significant_pairs = self.narrator._analyze_results() 
        self.assertEqual(len(significant_pairs), 2, "Ожидалось нахождение двух значимых пар.")

        # Проверяем генерацию истории для успешного случая
        story = self.narrator.generate_story(significant_pairs)
        print("\n[TEST SUCCESS STORY]:\n", story)
        self.assertIn("работают как команда!", story)


    @mock.patch('pandas.read_csv')
    def test_scenario_no_significance(self, mock_pd_read_csv):
        """Тест сценария: не найдено ни одной статистически значимой связи."""
        # 1. Создаем мок-данные для симуляции пустой или незначительной загрузки CSV
        mock_df = pd.DataFrame({
            'Detector1': ['WSPR', 'NGL'],
            'Detector2': ['A', 'B'],
            'Correlation_Strength(r)': [0.3, 0.4], # Слабые связи
            'P_Value': [0.2, 0.5],              # Высокий P-value (Незначимо)
            'FDR_Adjusted_P': [0.8, 0.7],    
            'Significant_Pair': ['False', 'False']
        })
        mock_pd_read_csv.return_value = mock_df

        # Запускаем анализ (логика должна вернуть пустой список)
        significant_pairs = self.narrator._analyze_results() 
        self.assertEqual(len(significant_pairs), 0, "Ожидалось обнаружение нулевых значимых пар.")

        # Проверяем генерацию истории для случая "Нет связи"
        story = self.narrator.generate_story([])
        print("\n[TEST NO-SIGNAL STORY]:\n", story)
        self.assertIn("призрак спрятался", story, "История должна соответствовать сценарию 'нет сигнала'.")

if __name__ == '__main__':
    unittest.main()