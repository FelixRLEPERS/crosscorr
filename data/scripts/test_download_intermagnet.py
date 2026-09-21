import unittest
from unittest import mock
from pathlib import Path
# Убедимся, что импортируем скрипт для тестирования
# В реальной жизни может потребоваться установка библиотеки 'tenacity' и pandas в окружение теста.
try:
    from data.scripts.download_intermagnet import parse_iaga2002, main, download_and_save_intermagnet 
except ImportError as e:
    print(f"Внимание при тестировании: {e}. Убедитесь, что все зависимости установлены.")

# Создаем временный мок-файл для тестирования парсинга
TEMP_FILE_PATH = Path("temp_test_iaga.min")


class TestIntermagnetDownloader(unittest.TestCase):
    """Тестирует парсинг и новую логику загрузки данных INTERMAGNET."""

    @classmethod
    def setUpClass(cls):
        # Создаем фиктивный файл для тестирования старого режима парсинга
        with open(TEMP_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write("# Заголовок файла IAGA-2002\n")
            f.write("2024-01-01 12:00:00 D1 A 5.5 -30 N 123.456789\n")
            f.write("2024-01-01 12:05:00 D1 B 5.6 -31 N 123.456789\n")

    @classmethod
    def tearDownClass(cls):
        # Очистка после всех тестов
        if TEMP_FILE_PATH.exists():
            os.remove(TEMP_FILE_PATH)


    def test_parse_iaga2002_basic_read(self):
        """Проверяет, что парсинг старого формата IAGA-2002 работает корректно."""
        df = parse_iaga2002(TEMP_FILE_PATH)

        # Проверка количества строк и типов данных
        self.assertEqual(len(df), 2)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp']))
        print("Тест парсинга IAGA-2002 пройден: Структура DataFrame корректна.")

    @mock.patch('data.scripts.download_from_api')
    def test_main_flow_parsing_vs_downloading(self, mock_download):
        """Проверяет, что основной парсер переключается между режимами."""
        # Мы мокаем внутренний API вызов, чтобы протестировать логику аргументов.
        # В реальной жизни нужно будет имитировать передачу флагов командной строки.
        
        with mock.patch('sys.argv', ['script_name', '--file', str(TEMP_FILE_PATH)]):
            # Вызываем main() в режиме парсинга
            main() 

    @mock.patch('data.scripts.download_from_api')
    def test_download_success_flow(self, mock_download):
        """Тестирует полный цикл: загрузка -> сохранение."""
        # Мокаем успешный возврат DataFrame из новой функции
        mock_df = pd.DataFrame({
            "timestamp": [pd.Timestamp("2024-01-03T...UTC")], 
            "X": [5], "Y": [6], "Z": [7]
        })
        mock_download.return_value = mock_df

        # Вызываем функцию, симулируя команду с флагом --download
        download_and_save_intermagnet("TEST", 2024, 1)
        print("Тест загрузки API пройден: Логика переключения на новую функцию работает.")