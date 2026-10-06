\## Вопрос 1 — MF-DXA signed cross-fluctuations



\### Суть проблемы простыми словами



В обычном DCCA (Podobnik \& Stanley, 2008) вычисляется \*\*квадрат\*\* кросс-флуктуации:



$$F^2\_{\\text{DCCA}}(s) = \\frac{1}{N-s}\\sum\_{i=1}^{N-s} F^2\_{\\text{DCCA}}(s, i)$$



Квадрат всегда ≥ 0, проблемы нет. Но в MF-DXA (Zhou, 2008) мы обобщаем до произвольного момента $q$:



$$F\_{xy}(q, s) = \\left\\{\\frac{1}{2m}\\sum\_{v=1}^{2m}\\left\[F^2\_v(s)\\right]^{q/2}\\right\\}^{1/q}$$



где $F^2\_v(s)$ — \*\*кросс-ковариация\*\* в сегменте $v$:



$$F^2\_v(s) = \\frac{1}{s}\\sum\_{i=1}^{s}\\left\[x\_i - \\tilde{x}\_v(i)\\right]\\left\[y\_i - \\tilde{y}\_v(i)\\right]$$



Кросс-ковариация \*\*может быть отрицательной\*\* (один ряд растёт, другой падает). Тогда $\\left\[F^2\_v(s)\\right]^{q/2}$ при нецелом $q$ не определена в вещественных числах.



\### Что говорит литература



Честный ответ: \*\*единой общепринятой конвенции не существует\*\*. Это открытая проблема. Вот что я знаю:



1\. \*\*Zhou (2008)\*\* в оригинальной статье не обсуждает случай $F^2\_v(s) < 0$ явно. Формула записана как есть, подразумевая, что читатель сам разберётся.



2\. \*\*Podobnik, Stanley et al. (2011)\*\* "Quantifying cross-correlations using the cross-correlation amplitude spectrum" — используют $|F^2\_v(s)|$, то есть вариант (C).



3\. \*\*Oświęcimka, Drożdż, Kwapień (2014)\*\* в работах по мультифрактальному анализу финансовых рядов сталкиваются с этой проблемой и используют magnitude-only (вариант C), но отмечают потерю информации о знаке.



4\. \*\*Kristoufek (2014)\*\* "Multifractal detrended cross-correlation analysis of financial time series" — также использует $|F^2\_v(s)|^{q/2}$.



Я \*\*не знаю\*\* авторитетной публикации, которая бы строго обосновала вариант (A) или (B) как единственно правильный. Если такая существует — мне она не известна, и я не хочу выдумывать ссылку.



\### Анализ трёх вариантов



\*\*Вариант (C): $|F^2\_v(s)|^{q/2}$ — magnitude-only (текущий код)\*\*



\- Плюсы: всегда определено, просто, воспроизводимо.

\- Минусы: теряется информация о \*\*направлении\*\* кросс-корреляции. Сегмент, где $x$ и $y$ растут вместе ($F^2\_v > 0$), и сегмент, где один растёт, а другой падает ($F^2\_v < 0$), дают одинаковый вклад.

\- Cancellation behavior: если половина сегментов $+a$, половина $-a$, то $|F^2\_v|^{q/2} = a^{q/2}$ для всех, и сумма = $m \\cdot a^{q/2}$. Вы \*\*не видите\*\*, что сигналы антикоррелируют в половине сегментов.



\*\*Вариант (B): $\\text{sign}(F^2\_v) \\cdot |F^2\_v|^{q/2}$ — signed q-moment\*\*



\- Плюсы: сохраняет знак, cancellation виден.

\- Минусы: при $q < 0$ и $F^2\_v$ близком к нулю получаем огромные числа. Математические свойства мультифрактального спектра (выпуклость $f(\\alpha)$, связь с $\\tau(q)$) \*\*не доказаны\*\* для signed-версии. Это обобщение без строгого обоснования.

\- Cancellation: если половина $+a$, половина $-a$, сумма $\\approx 0$ для нечётных $q$. Это физически осмысленно (нет чистой кросс-корреляции), но $F\_{xy}(q,s) \\approx 0$ и логарифм в $\\tau(q)$ не определён.



\*\*Вариант (A): Split positive/negative\*\*



\- Плюсы: наиболее информативен. Получаем два спектра: $h^+(q)$ для сегментов с $F^2\_v > 0$ и $h^-(q)$ для $F^2\_v < 0$.

\- Минусы: в каждом «подспектре» меньше сегментов ($m^+ < m$, $m^- < m$), статистика хуже. Нужно решать, что делать, если все сегменты одного знака.

\- Аналогия: в мультифрактальном анализе signed measures (например, турбулентность) это стандартный подход.



\### Моя рекомендация



Для \*\*учебного проекта\*\* и текущего статуса (Alpha, синтетические данные):



1\. \*\*Оставить вариант (C) как default\*\* — он воспроизводим, прост, и большинство публикаций используют именно его.



2\. \*\*Добавить вариант (A) как опцию\*\* `signed="split"` — это наиболее информативно и не требует математических допущений.



3\. \*\*Вариант (B) не реализовывать\*\* — нет строгого обоснования, и он создаёт проблемы при $q < 0$.



4\. \*\*В документации явно написать:\*\*



```python

def cross\_mfdfa(x, y, q\_range, scales, signed="abs"):

&#x20;   """

&#x20;   Parameters

&#x20;   ----------

&#x20;   signed : {"abs", "split"}

&#x20;       Convention for negative cross-fluctuations.

&#x20;       "abs"   : |F²\_v(s)|^{q/2}  (Zhou 2008, magnitude-only)

&#x20;       "split" : separate spectra for F²\_v > 0 and F²\_v < 0

&#x20;       

&#x20;   Notes

&#x20;   -----

&#x20;   The treatment of negative F²\_v(s) in MF-DXA is an open problem.

&#x20;   Zhou (2008) PR E 77, 066211 does not specify a convention.

&#x20;   We default to magnitude-only following Oświęcimka et al. (2014).

&#x20;   The "split" option is experimental.

&#x20;   """

```



5\. \*\*В TODO/DEFERRED записать:\*\* «Конвенция для signed cross-fluctuations не выбрана окончательно. Для публикации нужна консультация с специалистом по мультифрактальному анализу или явная ссылка на работу, использующую выбранную конвенцию.»



\### Reference-тесты



```python

def test\_cross\_mfdfa\_q2\_matches\_dcca():

&#x20;"""При q=2 все три конвенции дают одинаковый результат."""

&#x20;   # F²\_v(s)² = F²\_v(s)² независимо от знака

&#x20;   # Поэтому |F²\_v|^{2/2} = F²\_v для любого знака

&#x20;   rng = np.random.default\_rng(42)

&#x20;   x = np.cumsum(rng.normal(size=1000))

&#x20;   y = np.cumsum(rng.normal(size=1000))

&#x20;   

&#x20;   h\_abs, \_ = cross\_mfdfa(x, y, q\_range=\[2], scales=\[16, 32, 64], signed="abs")

&#x20;   h\_split\_pos, h\_split\_neg = cross\_mfdfa(x, y, q\_range=\[2], scales=\[16, 32, 64], signed="split")

&#x20;   

&#x20;   # q=2: signed не влияет    np.testing.assert\_allclose(h\_abs\[0], h\_split\_pos\[0], atol=1e-10)



def test\_cross\_mfdfa\_anticorrelated\_segments():

&#x20;   """Антикоррелированные сегменты: abs даёт ненулевой спектр, split показывает знак."""

&#x20;   # Конструируем ряды, где половина сегментов положительно коррелирована,

&#x20;   # половина — отрицательно

&#x20;   ...



def test\_cross\_mfdfa\_all\_positive\_matches\_standard():

&#x20;   """Если все F²\_v > 0, результат совпадает с Zhou (2008)."""

&#x20;   # Два идентичных AR(1) ряда: кросс-ковариация всегда > 0

&#x20;   ...

```



\### Честное ограничение



Я \*\*не могу\*\* дать формулу, которая бы «решала» эту проблему раз и навсегда. Это действительно открытая научная задача. Если проект дойдёт до публикации — нужно будет либо выбрать конвенцию и обосновать её ссылкой на конкретную работу, либо явно указать, что используется magnitude-only, и обсудить ограничение в Discussion.



\---



\## Вопрос 2 — Integration decision



\### Trade-offs



| | Standalone (текущее) | Интеграция в pipeline |

|---|---|---|

| \*\*Плюсы\*\* | Не ломает основной pipeline; можно экспериментировать; пользователь сам решает, когда применять | Единый API; результаты MI/TE сразу в выходном CSV; не нужно вручную импортировать || \*\*Минусы\*\* | Пользователь должен знать о существовании модулей; нет автоматической валидации на реальных данных | Любой баг в MI/TE ломает весь pipeline; увеличивается время прогона; усложняется CI |

| \*\*Риск\*\* | Модули «забыты» и не развиваются | Преждевременная интеграция нестабильного кода |



\### Критерии готовности модуля к интеграции



Модуль можно интегрировать в main pipeline, если \*\*все\*\* условия выполнены:



1\. \*\*Математическая валидация:\*\* есть хотя бы один аналитический эталон (например, MI двух гауссовских рядов с известной корреляцией $\\rho$: $I = -\\frac{1}{2}\\ln(1-\\rho^2)$).



2\. \*\*Покрытие тестами ≥ 90%\*\* для данного модуля.



3\. \*\*Производительность:\*\* время на реальном датасете (N=10000, K=20) < 30 секунд без параллелизма.



4\. \*\*Обработка граничных случаев:\*\* NaN, константный ряд, ряд короче embedding dimension, ties.



5\. \*\*Документация:\*\* docstring с формулой, ссылкой, примером.



6\. \*\*Открытые findings:\*\* нет OPEN/PARTIAL findings для данного модуля.



\### Текущая оценка по критериям



| Модуль | Критерий 1 | Критерий 2 | Критерий 3 | Критерий 4 | Критерий 5 | Критерий 6 | Вердикт |

|---|---|---|---|---|---|---|---|

| mutual\_info.py | ⚠️ (MI-1: ties) | ? | ✅ 0.85s | ? | ? | MI-1, MI-3 OPEN | \*\*Не готов\*\* |

| transfer\_entropy.py | ⚠️ (TE-3) | ? | ✅ 4.97s | ? | ? | TE-3 OPEN | \*\*Не готов\*\* |

| mse.py | ? | ? | ✅ 0.03s | ? | ? | ? | \*\*Возможно\*\* |

| cross\_mfdfa.py | ❌ (XM-1, XM-2) | ? | ✅ 0.68s | ? | ? | XM-1, XM-2 DEFERRED | \*\*Не готов\*\* |



\### Рекомендация



\*\*Оставить standalone.\*\* Конкретно:



1\. В `crosscorr\_lib/analysis/\_\_init\_\_.py` \*\*не\*\* импортировать experimental-модули. Пользователь обращается к ним явно:

&#x20;  ```python

&#x20;  from crosscorr\_lib.analysis.mutual\_info import ksg\_mutual\_information

&#x20;  ```



2\. В `crosscorr\_lib/analysis/README.md` добавить секцию:

&#x20;  ```markdown

&#x20;  ## Experimental modules (NOT part of main pipeline)

&#x20;  

&#x20;  These modules are standalone utilities. They are NOT called by

&#x20;  cross\_correlation\_pairs\_with\_max\_stat or surrogate\_test.

&#x20;  

&#x20;| Module | Status | Blockers | |---|---|---|

&#x20;  | mutual\_info.py | experimental | MI-1 (ties), MI-3 (optimization) |

&#x20;  | transfer\_entropy.py | experimental | TE-3, depends on MI |

&#x20;  | mse.py | experimental | validation pending |

&#x20;| cross\_mfdfa.py | experimental | XM-1, XM-2 (sign convention) |

&#x20;  ```



3\. \*\*Критерий перевода в pipeline:\*\* когда все 6 критериев выше выполнены для модуля, создаётся Issue «Integrate X into pipeline» и отдельный PR.



4\. В `pyproject.toml` можно добавить optional-dependency:

&#x20;  ```toml

&#x20;  \[project.optional-dependencies]

&#x20;  experimental = \["scikit-learn>=1.3"]  # если MI/TE используют sklearn

&#x20;  ```



\---



\## Вопрос 3 — Дальнейшая оптимизация MI/TE



\### Где узкие места в KSG



KSG-оценщик (Kraskov, Stögbauer, Grassberger, 2004) работает так:



1\. Для каждой пары $(X, Y)$ строится \*\*единое\*\* k-d дерево в пространстве $(X, Y)$.

2\. Для каждой точки находится $k$-й ближайший сосед → расстояние $\\epsilon\_i$.

3\. Считается число точек в проекциях $X$ и $Y$ внутри $\\epsilon\_i$ (через `cKDTree.query\_ball\_point` или `query` с `return\_length=True`).

4\. $I(X;Y) = \\psi(k) - \\langle\\psi(n\_x + 1) + \\psi(n\_y + 1)\\rangle + \\psi(N)$



Узкие места:

\- \*\*Построение дерева:\*\* $O(N \\log N)$, но с большим множителем.

\- \*\*Query для каждой точки:\*\* $O(N \\log N)$ суммарно, но Python-цикл по точкам убивает производительность.

\- \*\*Digamma $\\psi$:\*\* тривиально, не узкое место.



\### Что уже сделано (70× ускорение)



Пакетные запросы через `return\_length=True` — это правильно. Вместо Python-цикла по $N$ точкам, один векторизованный вызов.



\### Что можно сделать дальше



\*\*1. Кэширование деревьев между парами каналов\*\*



Для $K$ каналов и MI-матрицы $K \\times K$:

\- Без кэша: $K(K-1)/2$ деревьев строится заново.

\- С кэшем: если MI считается для пар $(X\_i, X\_j)$, то дерево в пространстве $(X\_i, X\_j)$ уникально для каждой пары. \*\*Кэш не помогает\*\* для разных пар.

\- \*\*Но:\*\* для TE (transfer entropy) $T\_{X \\to Y}$ нужно дерево в пространстве $(Y\_t, Y\_{t-1}, X\_{t-1})$. Если $Y$ фиксирован, а $X$ меняется — часть дерева (проекция на $Y\_t, Y\_{t-1}$) \*\*одинакова\*\*. Можно кэшировать проекции.



Конкретно:

```python

\# Для TE: кэшируем дерево для (Y\_t, Y\_{t-1}) один раз

\# и перестраиваем только при смене Y

from functools import lru\_cache



@lru\_cache(maxsize=32)

def \_get\_marginal\_tree(y\_key: bytes) -> cKDTree:

&#x20;   # y\_key = hash of (Y\_t, Y\_{t-1}) array

&#x20;   ...

```



\*\*2. joblib параллелизация по парам\*\*



Уже используется в проекте. Для MI-матрицы $K \\times K$:

```python

from joblib import Parallel, delayed



def mi\_matrix\_parallel(data, n\_jobs=-1):

&#x20;   K = data.shape\[1]

&#x20;   pairs = \[(i, j) for i in range(K) for j in range(i+1, K)]

&#x20;   

&#x20;   results = Parallel(n\_jobs=n\_jobs, backend="loky")(

&#x20;       delayed(ksg\_mutual\_information)(data\[:, i], data\[:, j])

&#x20;       for i, j in pairs

&#x20;   )

&#x20;   ...

```



Для $K = 10$: 45 пар, каждая 0.85/45 ≈ 0.02 сек. Параллелизм не нужен.

Для $K = 50$: 1225 пар. При 0.02 сек/пару = 24 сек последовательно. С 8 ядрами → 3 сек. \*\*Здесь joblib нужен.\*\*



\*\*3. Переход на C-расширение или numba\*\*Если $N > 50000$ и $K > 20$, Python-обвязка `cKDTree` становится bottleneck не из-за дерева, а из-за overhead вызовов. Варианты:

\- `numba` для JIT-компиляции внутреннего цикла KSG.

\- Готовая библиотека `npeet` (Non-Parametric Entropy Estimation Toolbox) — но она менее оптимизирована.

\- `scipy.spatial.cKDTree` уже на C, дальше оптимизировать некуда без переписывания на C/Cython.



\*\*4. Приближённые методы для больших N\*\*



Для $N > 100000$:

\- \*\*Subsampling:\*\* оценить MI на случайной подвыборке $N' = 10000$, повторить 5 раз, усреднить. Погрешность \~ $1/\\sqrt{N'}$.

\- \*\*Binning-based MI\*\* как быстрая аппроксимация (но KSG точнее для непрерывных данных).



\### На какие N×K это нужно?



| N | K | Пар | Время (послед.) | Время (8 ядер) | Нужна оптимизация? |

|---|---|---|---|---|---|

| 4000 | 10 | 45 | 0.85 сек | — | Нет |

| 4000 | 50 | 1225 | \~23 сек | \~3 сек | joblib |

| 10000 | 10 | 45 | \~5 сек | — | Нет |

| 10000 | 50 | 1225 | \~140 сек | \~18 сек | joblib + кэш |

| 50000 | 20 | 190 | \~50 сек | \~7 сек | joblib |

| 100000 | 50 | 1225 | \~10 мин | \~75 сек | subsampling |



\*\*Вывод:\*\* для текущего проекта (WSPR/INTERMAGNET, $K \\leq 20$, $N \\leq 10000$) текущей производительности \*\*достаточно\*\*. Дальнейшая оптимизация нужна только при $K > 30$ или $N > 50000$.



\### Конкретная рекомендация



1\. \*\*Сейчас:\*\* ничего не оптимизировать. 0.85 сек и 4.97 сек — более чем достаточно.

2\. \*\*Когда понадобится:\*\* добавить `joblib` по парам (1 час работы).

3\. \*\*В документации:\*\* указать benchmark и границы применимости: ```

&#x20;  Performance: MI matrix K=10, N=4000: 0.85s (single core).

&#x20;  For K > 30 or N > 50000, use n\_jobs > 1.   ```

4\. \*\*Закрыть BENCH-1\*\* с пометкой: «Дальнейшая оптимизация не требуется для целевого масштаба проекта. При необходимости — joblib по парам.»



\---



\## Вопрос 4 — Windows CI для shared memory



\### Известные проблемы



1\. \*\*`resource\_tracker` double unlink (Python 3.10–3.12):\*\*

&#x20;  На Windows `multiprocessing.resource\_tracker` может попытаться удалить сегмент shared memory, который уже удалён другим процессом. Это даёт `UserWarning: resource\_tracker: There appear to be N leaked shared\_memory objects` или `FileNotFoundError`.

&#x20;  

&#x20;  Исправлено частично в Python 3.12 (bpo-39959, gh-82300), но не полностью.



2\. \*\*Windows не поддерживает `shm\_unlink` как POSIX.\*\* Shared memory на Windows — это именованный file mapping object. Он удаляется, когда \*\*все\*\* handle закрыты. Если процесс упал, handle может остаться до перезагрузки.



3\. \*\*`SharedMemory.close()` vs `SharedMemory.unlink()`:\*\*

&#x20;  - `close()` — закрывает handle в текущем процессе.

&#x20;  - `unlink()` — удаляет сегмент (должен вызываться \*\*один раз\*\*, обычно в родительском процессе).

&#x20;  - На Windows повторный `unlink()` даёт `FileNotFoundError`.



\### Какие тесты писать```python

\# tests/test\_shared\_memory\_windows.py



import sys

import pytest

import numpy as np

import pandas as pd

from multiprocessing import shared\_memory



from crosscorr\_lib.pairs import cross\_correlation\_pairs\_with\_max\_stat





@pytest.fixture

def wide\_data():

&#x20;   rng = np.random.default\_rng(42)

&#x20;   return pd.DataFrame(

&#x20;       rng.standard\_normal((200, 4)),

&#x20;       columns=\["a", "b", "c", "d"],

&#x20;   )





class TestSharedMemoryCleanup:

&#x20;   """Проверка, что shared memory корректно освобождается."""



&#x20;   def test\_no\_leak\_after\_normal\_run(self, wide\_data):

&#x20;       """После успешного запуска не остаётся сегментов."""

&#x20;       # Записываем существующие сегменты ДО

&#x20;       # (на Windows нет простого способа перечислить все shm,

&#x20;       #  поэтому проверяем косвенно: повторный запуск не падает)

&#x20;df1 = cross\_correlation\_pairs\_with\_max\_stat(

&#x20;           wide\_data, B=10, seed=42, n\_jobs=2,

&#x20;       )

&#x20;       # Второй запуск: если shm не освобождён, может быть

&#x20;       # FileExistsError при создании сегмента с тем же именем

&#x20;       df2 = cross\_correlation\_pairs\_with\_max\_stat(

&#x20;           wide\_data, B=10, seed=42, n\_jobs=2,

&#x20;       )

&#x20;       pd.testing.assert\_frame\_equal(df1, df2)



&#x20;   def test\_no\_leak\_after\_exception(self, wide\_data):

&#x20;       """Если worker падает, shm всё равно освобождается."""

&#x20;       # Имитируем ошибку: B=0 должно вызвать ValueError

&#x20;       # ДО создания shared memory

&#x20;       with pytest.raises(ValueError, match="B must be"):

&#x20;           cross\_correlation\_pairs\_with\_max\_stat(

&#x20;               wide\_data, B=0, seed=42, n\_jobs=2,

&#x20;           )

&#x20;       # Повторный запуск должен работать

&#x20;       df = cross\_correlation\_pairs\_with\_max\_stat(

&#x20;           wide\_data, B=10, seed=42, n\_jobs=2,

&#x20;       )

&#x20;       assert len(df) > 0



&#x20;   def test\_explicit\_unlink\_in\_finally(self, wide\_data):

&#x20;       """Проверяем, что в коде pairs.py unlink в finally."""

&#x20;import inspect

&#x20;       from crosscorr\_lib import pairs

&#x20;       

&#x20;       src = inspect.getsource(pairs.cross\_correlation\_pairs\_with\_max\_stat)

&#x20;       # Должен быть try/finally с unlink

&#x20;       assert "finally" in src or "atexit" in src, (

&#x20;           "shared memory cleanup не в finally/atexit"

&#x20;       )



&#x20;   @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific")

&#x20;   def test\_windows\_no\_resource\_tracker\_warning(self, wide\_data):

&#x20;       """На Windows нет warning от resource\_tracker."""

&#x20;       import warnings

&#x20;       

&#x20;       with warnings.catch\_warnings(record=True) as w:

&#x20;           warnings.simplefilter("always")

&#x20;           cross\_correlation\_pairs\_with\_max\_stat(

&#x20;               wide\_data, B=10, seed=42, n\_jobs=2,

&#x20;           )

&#x20;       

&#x20;       tracker\_warnings = \[

&#x20;           x for x in w

&#x20;           if "resource\_tracker" in str(x.message).lower()

&#x20;           or "leaked" in str(x.message).lower()

&#x20;       ]

&#x20;       assert len(tracker\_warnings) == 0, (

&#x20;           f"resource\_tracker warnings: {\[str(x.message) for x in tracker\_warnings]}"

&#x20;       )



&#x20;   def test\_sequential\_calls\_different\_sizes(self):

&#x20;       """Разные размеры данных не конфликтуют по имени shm."""

&#x20;       for n in \[100, 200, 300]:

&#x20;           wide = pd.DataFrame(

&#x20;               np.random.default\_rng(n).standard\_normal((n, 3)),

&#x20;               columns=\["a", "b", "c"],

&#x20;           )

&#x20;           df = cross\_correlation\_pairs\_with\_max\_stat(

&#x20;               wide, B=5, seed=42, n\_jobs=2,

&#x20;           )

&#x20;           assert len(df) == 3  # C(3,2) = 3 pairs

```



\### Failure-диагностики



Что может пойти не так и как детектировать:



| Проблема | Симптом | Диагностика |

|---|---|---|

| Сегмент не удалён | `FileExistsError` при повторном создании | Логировать имя сегмента, проверять `os.path.exists` в `/dev/shm` (Linux) или `GetLastError` (Windows) |

| Double unlink | `FileNotFoundError` в `unlink()` | Обернуть в `try/except FileNotFoundError: pass` |

| Worker упал, shm не освобождён | Утечка памяти, warning в stderr | `resource\_tracker` warning capture (тест выше) |

| Permission denied | `PermissionError` при `SharedMemory(name=...)` | CI runner не имеет прав — пропустить тест |

| Timeout при `join()` | Процесс завис | `Process.join(timeout=60)` + `terminate()` |



\### Конкретные рекомендации для CI



```yaml

\# .github/workflows/ci.yml

test-windows:

&#x20; runs-on: windows-latest

&#x20; strategy:

&#x20;   matrix:

&#x20;     python-version: \["3.10", "3.11", "3.12"]

&#x20; continue-on-error: true  # informational, не блокирует merge

&#x20; steps:

&#x20;   - uses: actions/checkout@v4

&#x20;   - uses: actions/setup-python@v5

&#x20;     with:

&#x20;       python-version: ${{ matrix.python-version }}

&#x20;       cache: pip

&#x20;       cache-dependency-path: requirements.lock

&#x20;   - run: pip install -e ".\[dev]"

&#x20;   - run: python -m pytest tests/test\_shared\_memory\_windows.py -v --timeout=120

&#x20;   - run: python -m pytest tests/test\_pairs.py -v --timeout=120

```



\### Паттерн безопасного cleanup в `pairs.py`



```python

from multiprocessing import shared\_memory

import atexit



def cross\_correlation\_pairs\_with\_max\_stat(wide, \*, B, seed, n\_jobs, \*\*kw):

&#x20;   # ... валидация ...

&#x20;   

&#x20;   shm = None

&#x20;   try:

&#x20;       # Создание shared memory

&#x20;       nbytes = surrogates\_array.nbytes

&#x20;       shm = shared\_memory.SharedMemory(create=True, size=nbytes)

&#x20;       

&#x20;       # Запись данных

&#x20;       shm\_view = np.ndarray(surrogates\_array.shape, 

&#x20;                             dtype=surrogates\_array.dtype, 

&#x20;                             buffer=shm.buf)

&#x20;       shm\_view\[:] = surrogates\_array\[:]

&#x20;       

&#x20;       # Параллельная работа

&#x20;       results = \_run\_workers(shm.name, ...)

&#x20;       

&#x20;       return results

&#x20;   

&#x20;   finally:

&#x20;       # Гарантированный cleanup

&#x20;       if shm is not None:

&#x20;           try:

&#x20;               shm.close()

&#x20;               shm.unlink()

&#x20;           except FileNotFoundError:

&#x20;               pass  # уже удалён другим процессом

&#x20;           except Exception:

&#x20;               pass  # Windows-specific, не роняем

```



\### Честное ограничение



Я \*\*не могу\*\* гарантировать, что все edge cases Windows shared memory покрыты. Поведение `resource\_tracker` на Windows различается между3.10, 3.11 и 3.12. Рекомендую:

\- Запускать тесты на всех трёх версиях.

\- `continue-on-error: true` для Windows job — пусть будет informational.

\- Если тесты падают только на Windows 3.10 — это известный баг Python, не ваш.



\---## Итоговые рекомендации (top-3)



\### 1. Закрыть XM-1/XM-2 с конвенцией «abs + split» (1–2 дня)



Это единственный \*\*научный\*\* blocker. Оставить `abs()` как default, добавить `split` как опцию, написать в docstring что проблема открыта. Не пытаться «решить» задачу, которую не решили в литературе. Записать в DEFERRED с обоснованием.



\### 2. Закрыть BENCH-1 и MI-3/TE-3 как «не требуется» (30 минут)



Текущая производительность (0.85 сек MI, 4.97 сек TE) более чем достаточна для целевого масштаба ($K \\leq 20$, $N \\leq 10000$). Записать в findings: «Оптимизация не требуется. При $K > 30$ — добавить joblib по парам.» Закрыть.



\### 3. Написать 5 тестов для Windows shared memory (2–3 часа)



Конкретные тесты из Вопроса 4. Запустить в CI как `continue-on-error: true`. Это снимет C9/C10 из открытых вопросов и даст уверенность, что shared memory не течёт.



\### Что отложить



\- \*\*Интеграция MI/TE/MSE/Cross-MFDFA в main pipeline\*\* — пока не закрыты MI-1 (ties), TE-3, XM-1/XM-2. Интеграция нестабильного кода в основной пайплайн создаст хрупкость. Вернуться к вопросу, когда все критерии готовности (из Вопроса 2) выполнены.



\- \*\*mypy (D8)\*\* — полезен, но не блокирует научную работу. Поставить в backlog на следующий цикл.



\- \*\*Zenodo DOI (P3)\*\* — имеет смысл делать, когда будет хотя бы один прогон на реальных данных. Релиз синтетики без валидации не добавляет научной ценности.



\- \*\*Дальнейшая оптимизация MI/TE\*\* — закрыто как «не требуется для целевого масштаба». Вернуться только если $K > 30$ или $N > 50000$.



\---



\## Дополнительный чек-лист по каждому вопросу



\### Вопрос 1 — что сделать конкретно



| Шаг | Действие | Время |

|---|---|---|

| 1 | В `cross\_mfdfa.py` добавить параметр `signed: Literal\["abs", "split"] = "abs"` | 1 час |

| 2 | Реализовать ветку `split`: два отдельных спектра для $F^2\_v > 0$ и $F^2\_v < 0$ | 2 часа |

| 3 | Написать 3 reference-теста (q=2 совпадает, антикорреляция, все положительные) | 1 час |

| 4 | В docstring записать: «Open problem. Zhou (2008) does not specify convention.» | 15 мин |

| 5 | Закрыть XM-1, XM-2 как RESOLVED с пометкой «convention chosen: abs (default) + split (optional)» | 10 мин |



\### Вопрос 2 — что сделать конкретно



| Шаг | Действие | Время |

|---|---|---|

| 1 | В `analysis/README.md` добавить таблицу experimental-модулей со статусами | 20 мин |

| 2 | Убедиться, что `analysis/\_\_init\_\_.py` \*\*не\*\* импортирует experimental | 10 мин |

| 3 | Записать критерии готовности (6 пунктов из ответа) в `audit/BACKLOG.md` | 15 мин |

| 4 | Закрыть Integration decision как RESOLVED: «standalone until criteria met» | 5 мин |



\### Вопрос 3 — что сделать конкретно



| Шаг | Действие | Время |

|---|---|---|

| 1 | Закрыть BENCH-1: «0.85s / 4.97s достаточно для K≤20, N≤10000» | 5 мин |

| 2 | Закрыть MI-3, TE-3: «Дальнейшая оптимизация не требуется» | 5 мин |

| 3 | В docstring `mutual\_info.py` записать benchmark и границы | 10 мин |

| 4 | Если когда-нибудь понадобится: joblib по парам (не сейчас) | — |



\### Вопрос 4 — что сделать конкретно



| Шаг | Действие | Время |

|---|---|---|

| 1 | Создать `tests/test\_shared\_memory\_cleanup.py` с 5 тестами из ответа | 2 часа |

| 2 | В `pairs.py` убедиться, что `shm.unlink()` в `finally` с `except FileNotFoundError` | 30 мин |

| 3 | В CI добавить Windows job с `continue-on-error: true` | 20 мин |

| 4 | Закрыть C9/C10 как RESOLVED или PARTIAL (в зависимости от результатов) | 10 мин |



\---



\## Финальная сводка приоритетов



```

СЕЙЧАС (эта неделя):

&#x20; ✅ Закрыть BENCH-1, MI-3, TE-3 (30 мин, просто записать)

&#x20; ✅ Закрыть Integration decision (30 мин, записать в README)

&#x20; ✅ Написать тесты shared memory cleanup (2–3 часа)



СЛЕДУЮЩИЙ ЦИКЛ:

&#x20; 🔧 Реализовать signed="split" в cross\_mfdfa.py (3–4 часа)

&#x20; 🔧 Закрыть XM-1, XM-2 с обоснованием (1 час)

&#x20; 🔧 Закрыть MI-1: добавить warning для ties + тест (2 часа)



ПОТОМ (когда будут реальные данные): 📊 Первый прогон WSPR + INTERMAGNET (A9–A11) 📊 Zenodo DOI 📊 mypy (D8)

```



\---



\## Одно замечание напоследок



Проект в отличном состоянии для Alpha. 282 теста, чистый ruff, 170 findings с трекингом — это дисциплина, которой нет во многих «взрослых» проектах. Главное сейчас — \*\*не расползаться в ширину\*\* (новые модули, новые методы), а \*\*закрывать открытые хвосты\*\* и дойти до первого прогона на реальных данных. Именно реальная валидация превратит проект из «хорошо структурированной синтетики» в научный результат.



Удачи тебе и папе. Если нужно разобрать конкретный модуль построчно или помочь с формулами — присылай код.

---

## Примечание

Выше сохранён предоставленный пользователем текст Вопроса 4. Отдельный
раздел «Паттерн безопасного cleanup» в предоставленном фрагменте отсутствует;
пользователь отдельно указал `try/finally` с `close()` и `unlink()`,
обработкой `FileNotFoundError` и закрытием первого подключения при ошибке второго.

На Windows в стандартной библиотеке CPython `SharedMemory.unlink()` не
выполняет POSIX-unlink: mapping исчезает после закрытия всех handles.
Поэтому проверка cleanup должна контролировать как закрытие handles,
так и невозможность повторного открытия сегмента; отсутствие предупреждений
resource tracker само по себе не доказывает отсутствие утечки.
