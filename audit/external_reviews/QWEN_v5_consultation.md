## Вопрос 4 — Windows CI для shared memory

### Известные проблемы

1. resource_tracker double unlink (Python 3.10–3.12):
   На Windows multiprocessing.resource_tracker может попытаться
   удалить сегмент shared memory, который уже удалён другим
   процессом. Это даёт UserWarning: resource_tracker: There appear
   to be N leaked shared_memory objects или FileNotFoundError.
   Исправлено частично в Python 3.12, но не полностью.

2. Windows не поддерживает shm_unlink как POSIX. Shared memory
   на Windows — это именованный file mapping object. Он удаляется,
   когда все handle закрыты. Если процесс упал, handle может
   остаться до перезагрузки.

3. SharedMemory.close() vs SharedMemory.unlink():
   - close() — закрывает handle в текущем процессе.
   - unlink() — удаляет сегмент (должен вызываться один раз,
     обычно в родительском процессе).
   - На Windows повторный unlink() даёт FileNotFoundError.

### Какие тесты писать

```python
# tests/test_shared_memory_windows.py

import sys
import pytest
import numpy as np
import pandas as pd
from multiprocessing import shared_memory

from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat


@pytest.fixture
def wide_data():
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        rng.standard_normal((200, 4)),
        columns=["a", "b", "c", "d"],
    )


class TestSharedMemoryCleanup:
    """Проверка, что shared memory корректно освобождается."""

    def test_no_leak_after_normal_run(self, wide_data):
        """После успешного запуска не остаётся сегментов."""
        df1 = cross_correlation_pairs_with_max_stat(
            wide_data, B=10, seed=42, n_jobs=2,
        )
        df2 = cross_correlation_pairs_with_max_stat(
            wide_data, B=10, seed=42, n_jobs=2,
        )
        pd.testing.assert_frame_equal(df1, df2)

    def test_no_leak_after_exception(self, wide_data):
        """Если worker падает, shm всё равно освобождается."""
        with pytest.raises(ValueError, match="B must be"):
            cross_correlation_pairs_with_max_stat(
                wide_data, B=0, seed=42, n_jobs=2,
            )
        df = cross_correlation_pairs_with_max_stat(
            wide_data, B=10, seed=42, n_jobs=2,
        )
        assert len(df) > 0

    def test_explicit_unlink_in_finally(self, wide_data):
        """Проверяем, что в коде pairs.py unlink в finally."""
        import inspect
        from crosscorr_lib import pairs
        src = inspect.getsource(
            pairs.cross_correlation_pairs_with_max_stat
        )
        assert "finally" in src or "atexit" in src, (
            "shared memory cleanup не в finally/atexit"
        )

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific")
    def test_windows_no_resource_tracker_warning(self, wide_data):
        """На Windows нет warning от resource_tracker."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cross_correlation_pairs_with_max_stat(
                wide_data, B=10, seed=42, n_jobs=2,
            )
        tracker_warnings = [
            x for x in w
            if "resource_tracker" in str(x.message).lower()
            or "leaked" in str(x.message).lower()
        ]
        assert len(tracker_warnings) == 0, (
            f"resource_tracker warnings: "
            f"{[str(x.message) for x in tracker_warnings]}"
        )

    def test_sequential_calls_different_sizes(self):
        """Разные размеры данных не конфликтуют по имени shm."""
        for n in [100, 200, 300]:
            wide = pd.DataFrame(
                np.random.default_rng(n).standard_normal((n, 3)),
                columns=["a", "b", "c"],
            )
            df = cross_correlation_pairs_with_max_stat(
                wide, B=5, seed=42, n_jobs=2,
            )
            assert len(df) == 3  # C(3,2) = 3 pairs
```

### Примечание к сохранённому фрагменту

Выше сохранён предоставленный пользователем текст Вопроса 4. Отдельный
раздел «Паттерн безопасного cleanup» в предоставленном фрагменте отсутствует;
пользователь отдельно указал `try/finally` с `close()` и `unlink()`,
обработкой `FileNotFoundError` и закрытием первого подключения при ошибке второго.

На Windows в стандартной библиотеке CPython `SharedMemory.unlink()` не
выполняет POSIX-unlink: mapping исчезает после закрытия всех handles.
Поэтому проверка cleanup должна контролировать как закрытие handles,
так и невозможность повторного открытия сегмента; отсутствие предупреждений
resource tracker само по себе не доказывает отсутствие утечки.
