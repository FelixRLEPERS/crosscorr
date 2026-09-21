import pandas as pd
from data.scripts import SourceRegistry
from code.narrator import narrate # Предполагаем, что это функция для озвучивания

# --- КОНСТАНТЫ ПУТЕЙ К ДАННЫМ ---
CC_CSV = "results/cross_correlation.csv"
SIG_CSV = "results/surrogate_significant.csv"
NARRATOR_MODULE = "code.narrator"

class AINarrator:
    """
    Оркестратор, который принимает научные данные и превращает их в 
    повествование для ребёнка (11-13 лет).
    """
    def __init__(self):
        pass

    def _analyze_results(self) -> list[tuple[str, str]]:
        """
        Читает CSV-файлы и извлекает пары детекторов с доказанной статистической значимостью.
        Возвращает список кортежей вида: [('D1', 'D2'), ...]
        """
        try:
            # Чтение данных - основной источник истины о связи
            df_sig = pd.read_csv(SIG_CSV)
        except FileNotFoundError:
            print(f"WARNING: Файл {SIG_CSV} не найден. Невозможно провести анализ.")
            return []

        if df_sig.empty:
            return []

        # Извлекаем только те пары, которые прошли ВСЕ проверки (это наш результат)
        significant_pairs = set()
        for index, row in df_sig.iterrows():
            # Предполагаем, что столбцы содержат детекторы A и B
            pair = tuple(sorted([row['Detector1'], row['Detector2']]))
            significant_pairs.add(pair)

        return list(significant_pairs)

    def generate_story(self, significant_pairs: list[tuple[str, str]]) -> str:
        """
        Генерирует текст повествования на основе найденных связей.
        """
        if not significant_pairs:
            # Сценарий 2: Ничего не найдено (Призрак спрятался)
            story = f"""
                (Тихий, таинственный голос): Хмм... Кажется, сегодня наш призрак был невероятно скрытным. 
                Значимой связи мы найти не смогли! Это значит, что нам нужно собрать больше данных или попробовать другой метод.
                Не расстраивайтесь! Мы просто ещё не знаем, где искать. Давайте поиграем в "угадай детектор" и подготовимся к завтрашнему дню!
            """
            return story

        # Сценарий 1: Успех - Связь найдена
        story_parts = [
            "Привет, юный исследователь!",
            "Похоже, наши кросс-корреляции дали нам невероятные новости!",
            "Мы обнаружили, что детекторы **{'**'.join([f'*{d}*' for d in significant_pairs])}** работают как команда! Это значит, что их сигналы часто совпадают и подтверждают друг друга. Это как два лучших друга, которые всегда говорят одно и то же!",
            "Это самая большая находка за неделю! Нам нужно детально изучить эти пары, чтобы понять научный смысл этой синхронности."
        ]
        
        # Комбинирование текста в единую историю
        full_story = " ".join(story_parts)
        return full_story.replace('**', '')

    def run_narrative(self):
        """Главный метод, запускающий полный пайплайн: Анализ -> Текст -> Голос."""
        print("--- AI Narrator запущен ---")
        
        # 1. Анализ результатов
        significant_pairs = self._analyze_results()

        if not significant_pairs:
            story = self.generate_story(significant_pairs)
            final_message = story
        else:
            story = self.generate_story(significant_pairs)
            final_message = story
        
        # 2. Озвучивание истории (Вызов внешнего модуля)
        try:
            narrate(final_message, speaker="Child", style="Excited")
            print("Narrator успешно запущен и озвучил финальную историю.")
        except Exception as e:
            print(f"ВНИМАНИЕ: Не удалось вызвать модуль narrator.py для озвучивания. Ошибка: {e}")

# Пример использования (для отладки)
if __name__ == "__main__":
    narrator = AINarrator()
    narrator.run_narrative()