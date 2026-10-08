# AUDIT_REPORT.md

> Внешний аудит: Reviewer 2, Space Weather (AGU / Wiley)
> Дата аудита: 2026-10-08
> Commit SHA на момент аудита: 284cf30
> Ветка: opencode/proud-wizard
> Оригинал: audit/REVIEWER2_FULL_AUDIT.txt

## TL;DR
- Overall score: 8.0/10 — Accept with minor revisions.
- arXiv: готово.
- Space Weather: готово при выполнении 3 MUST-задач (см. TODO.md).

## Полный отчёт

# ПОЛНЫЙ АУДИТ ПРОЕКТА CROSSCORR
## Reviewer 2 — Space Weather (AGU/Wiley)

---

## 1. ОБЩАЯ АРХИТЕКТУРА И СТРУКТУРА

### 1.1 Организация репозитория ✅ **Отлично**
```
crosscorr/
├── crosscorr_lib/analysis/    # 20 модулей статистического ядра
├── data/                      # ETL pipeline
│   ├── scripts/               # 13 скриптов загрузки/обработки
│   ├── raw/                   # (gitignored)
│   └── processed/             # unified.parquet (gitignored)
├── scripts/                   # 15 скриптов анализа
├── tests/                     # 291 тест
├── paper/                     # LaTeX article (AGU template)
├── docs/                      # 10+ MD документов
└── audit/                     # Версионированные аудиты
```

**Оценка:** Структура соответствует best practices для научных проектов (cookiecutter-data-science стиль). Четкое разделение library/analysis/pipeline — это профессиональный подход.

### 1.2 Зависимости и конфигурация ✅ **Хорошо**
- **pyproject.toml:** Современный стандарт PEP 621
- **Python 3.10+ requirement:** Разумный выбор
- **Optional dependencies:** Грамотная сегментация (astro, bayes, mfdfa, dev, all)
- **pip-tools:** requirements.lock для воспроизводимости

**⚠️ Замечание:** В `pyproject.toml` есть комментарий про MFDFA и smoke-тест. Это хороший знак того, что разработчики отслеживают зависимости тестов, но сам факт необходимости такого хака указывает на потенциальную проблему с изоляцией модулей.

---

## 2. КАЧЕСТВО КОДА И ИНЖЕНЕРИИ

### 2.1 Статический анализ ✅ **Отлично**
- **ruff:** Современный линтер (замена flake8+isort+black)
- **mypy:** Type checking включен в CI
- **pytest-cov:** Coverage tracking (91% для preprocessing.py)

### 2.2 Архитектура анализа ✅ **Профессионально**
Модули `crosscorr_lib/analysis/` демонстрируют зрелый подход:
- **separation of concerns:** Каждый модуль решает одну задачу
- **CLI interfaces:** Модули можно запускать как скрипты
- **Experimental modules:** Четкое разделение stable/experimental (mutual_info, transfer_entropy, mse, cross_mfdfa помечены как experimental с явными blockers)

### 2.3 Статистическое ядро ✅ **Впечатляюще**
Ключевые модули:
- `surrogate.py` (28 KB): Фазовые суррогаты, FDR (BY/BH), Davison-Hinkley bootstrap
- `block_bootstrap.py`: Block bootstrap для нестационарных рядов
- `effective_sample.py`: ESS/IAT calculation
- `residuals.py` (18 KB): MixedLM/OLS residual modeling
- `power_curve.py`: Statistical power analysis

**Оценка:** Это не "скрипт для анализа", а полноценная статистическая библиотека. Уровень зрелости соответствует академическим стандартам.

---

## 3. МЕТОДОЛОГИЯ И СТАТИСТИКА

### 3.1 Block Permutation Test ✅ **Корректно**
Анализ `scripts/perm_test_18mo_3band.py`:

```python
def block_perm_test(merged, block_size=24, n_iter=10000):
    # Residuals: value - mean(month × hour_of_day × day_of_week)
    # Block permutation preserves diurnal structure
    # Test statistic: mean(resid|storm) - mean(resid|quiet)
```

**Сильные стороны:**
- ✅ **Block size = 24h:** Сохраняет суточную структуру, предотвращает leakage
- ✅ **Residuals model:** Удаляет сезонные/недельные/суточные циклы
- ✅ **10,000 iterations:** Достаточная точность p-value (±0.0001)
- ✅ **Deterministic seed:** `np.random.default_rng(42)` для воспроизводимости

**⚠️ Потенциальная проблема:** Скрипт использует hardcoded period `'2024-04-01 .. 2025-09-30'`. Для true reproducibility этот параметр должен быть в config.yaml или CLI argument.

### 3.2 Pairwise Kp Bin Comparison ✅ **Корректно**
```python
bins = [
    ((5, 6), (6, 7), 'Kp 5-6 vs Kp 6-7'),
    ((6, 7), (7, 99), 'Kp 6-7 vs Kp 7+'),
    ((5, 6), (7, 99), 'Kp 5-6 vs Kp 7+'),
]
```

**Оценка:** Правильный подход к тестированию scale-dependence. Тестирование всех трех попарных сравнений (3 bins → 3 tests) с subsequent FDR correction — это методологически грамотно.

### 3.3 FDR Control ✅ **Применено верно**
В `surrogate.py` реализованы:
- **Benjamini-Hochberg (BH):** Для positive regression dependence
- **Benjamini-Yekutieli (BY):** Для arbitrary dependence (более консервативно)

**Оценка:** Наличие обоих методов показывает понимание проблемы multiple testing. Выбор метода должен быть обоснован в статье (предполагаю, что используется BH как менее консервативный).

---

## 4. ВОСПРОИЗВОДИМОСТЬ И ДАННЫЕ

### 4.1 Data Pipeline ✅ **Отлично**
ETL pipeline в `data/scripts/`:
- `fetch_all.py`: Оркестратор загрузки
- `download_wspr.py`, `download_space_weather.py`, etc.: Source-specific loaders
- `unify_schema.py`: Schema unification → `unified.parquet`

**Сильные стороны:**
- ✅ **Parquet format:** Эффективное хранение и чтение
- ✅ **Versioned schema:** `detector_type`, `detector_id`, `value`, `timestamp_utc`, `unit`, `quality_flag`
- ✅ **Config-driven:** `config.yaml` для параметров

**⚠️ Критическая проблема:** Данные `data/raw/` и `data/processed/unified.parquet` **gitignored**. Это означает, что для воспроизведения результатов рецензент должен:
1. Запустить `fetch_all.py` (требует доступа к wspr.live API)
2. Подождать ~5 сек/день × 550 дней = 45 минут
3. Надеяться, что API не изменился

**Решение:** Для true reproducibility перед submission в Space Weather вы **обязаны** либо:
- Загрузить `unified.parquet` в Zenodo/Figshare и добавить DOI в Data Availability statement
- Либо предоставить subset данных в репозитории (если < 100 MB)

**Без этого статья будет отклонена по формальным причинам.**

### 4.2 Data Sources ✅ **Comprehensive**
| Source | Resolution | Access |
|---|---|---|
| wspr.live | 1 hour | Public ClickHouse API |
| GFZ Potsdam | 3 hours | Public JSON |
| WDC Kyoto | 1 hour | Public |
| NOAA SWPC | Monthly | Public |
| JPL Horizons | 1 hour | Public API |

**Оценка:** Все источники публичные и стабильные. Использование независимого индекса (Dst) для валидации Kp — отличный методологический ход.

---

## 5. ДОКУМЕНТАЦИЯ

### 5.1 README.md ✅ **Отлично**
- **Quick start:** Четкие 4 шага для воспроизведения main result
- **Data sources table:** Понятная сводка
- **Repository layout:** Визуальная структура
- **⚠️ VPN warning:** Упоминание о необходимости VPN для wspr.live — важный практический нюанс

### 5.2 docs/ ✅ **Comprehensive**
- `DATA_PIPELINE.md` (16 KB): Детальное описание ETL
- `PIPELINE.md` (15 KB): Описание analysis pipeline
- `methodology.md` (14 KB): Методология
- `AI_ASSISTANCE.md`: Прозрачное признание использования AI (это **обязательно** для современных публикаций!)
- `first_result.md` (40 KB): Детальный отчет о результатах

**Оценка:** Документация на уровне профессиональных open-source проектов. Наличие `AI_ASSISTANCE.md` — это золотой стандарт прозрачности.

### 5.3 audit/ ✅ **Уникальная особенность**
Папка содержит 15+ аудитов (AUDIT_v1..v8, A_progress..G_progress, BACKLOG, STOP_DECISIONS).

**Оценка:** Это **беспрецедентный уровень прозрачности**. Ни один рецензент не сможет обвинить вас в сокрытии итераций или cherry-picking результатов. Это превращает проект в case study по reproducible research.

---

## 6. CI/CD И ТЕСТИРОВАНИЕ

### 6.1 GitHub Actions Workflow ✅ **Professional**
```yaml
jobs:
  check-changes:        # Path-based filtering
  test-fast:            # Python 3.11/3.12, ruff, mypy, pytest (not slow)
  test-slow:            # Conditional on analysis/ changes
  test-windows:         # Informational (continue-on-error)
```

**Сильные стороны:**
- ✅ **Path filtering:** Slow tests запускаются только при изменении `crosscorr_lib/analysis/`
- ✅ **Multi-version testing:** Python 3.11 + 3.12
- ✅ **Strict quality gates:** ruff + mypy + compileall + pytest
- ✅ **Windows job:** Проверка shared_memory cleanup (известная проблема cross-platform)

**⚠️ Замечание:** Coverage threshold `--cov-fail-under=45` — слишком низкий. Для научного проекта рекомендую минимум 70%.

### 6.2 Test Suite ✅ **Impressive**
**291 tests** в 30+ файлах:
- `test_residuals.py` (16 KB): Comprehensive residual testing
- `test_max_stat_pipeline.py` (7 KB): End-to-end max-stat test
- `test_negative_control.py` (4 KB): Negative control validation
- `test_ess_and_bootstrap.py` (9 KB): ESS/bootstrap correctness
- `test_fdr.py`: FDR control validation
- `test_shared_memory_cleanup.py` (7 KB): Windows-specific cleanup

**Оценка:** Test coverage на уровне production-grade software. Наличие negative controls и statistical reference tests — признак зрелой методологии.

---

## 7. СИЛЬНЫЕ СТОРОНЫ (STRENGTHS)

### 7.1 Методологическая строгость
- **Block permutation:** Правильный выбор для суточных данных
- **Residuals modeling:** Удаление confounders перед тестированием
- **Independent replication:** Held-out period (Jan-Mar 2026)
- **Multiple testing correction:** FDR (BH/BY)
- **Negative controls:** Проверка на ложноположительные срабатывания

### 7.2 Инженерная зрелость
- **Library architecture:** Переиспользуемые модули
- **Type hints + static analysis:** mypy + ruff
- **Comprehensive testing:** 291 tests
- **CI/CD:** Automated quality gates
- **Documentation:** 10+ KB docs на каждый компонент

### 7.3 Прозрачность
- **Versioned audits:** Полная история итераций
- **AI assistance disclosure:** Честное признание использования AI
- **Open data sources:** Все данные публичные
- **Reproducible pipeline:** One-command reproduction

### 7.4 Научная новизна
- **Baseline invariance:** Уникальное наблюдение о фиксированной популяции уязвимых трасс
- **Scale-dependence:** Нелинейный отклик на Kp
- **Dual mechanism:** MUF + D-layer интерпретация
- **Citizen science validation:** WSPR как распределенный сенсор

---

## 8. СЛАБЫЕ СТОРОНЫ И РИСКИ (WEAKNESSES)

### 8.1 Критические проблемы 🚨

#### 8.1.1 Отсутствие данных в репозитории
**Проблема:** `data/raw/` и `data/processed/unified.parquet` gitignored.
**Риск:** Рецензент не сможет воспроизвести результаты без запуска ETL pipeline.
**Решение:** Загрузить `unified.parquet` в Zenodo/Figshare, добавить DOI в статью.

#### 8.1.2 Small sample size в held-out
**Проблема:** N_storm = 23 hours (held-out) vs 198 hours (training).
**Риск:** Статистическая мощность недостаточна для надежной валидации.
**Решение:** Явно признать это в Limitations, подчеркнуть, что цель — проверка направления эффекта, а не точной величины.

#### 8.1.3 Spatial aggregation
**Проблема:** Глобальное усреднение спотов маскирует региональные эффекты (PCA vs mid-latitude MUF drop).
**Риск:** Потеря физической интерпретируемости.
**Решение:** Добавить в Future Work: "Great Circle path geometry analysis for spatial resolution."

### 8.2 Технические долги ⚠️

#### 8.2.1 Hardcoded periods
**Проблема:** `perm_test_18mo_3band.py` содержит hardcoded `'2024-04-01 .. 2025-09-30'`.
**Решение:** Параметризовать через CLI или config.yaml.

#### 8.2.2 Low coverage threshold
**Проблема:** `--cov-fail-under=45` в CI.
**Решение:** Повысить до 70% для scientific code.

#### 8.2.3 Experimental modules
**Проблема:** `mutual_info.py`, `transfer_entropy.py`, `mse.py`, `cross_mfdfa.py` помечены как experimental, но включены в репозиторий.
**Риск:** Рецензент может попытаться их использовать и получить некорректные результаты.
**Решение:** Либо довести до production quality, либо удалить из main branch (оставить в отдельной experimental branch).

### 8.3 Научные риски ⚠️

#### 8.3.1 Overclaiming baseline invariance
**Проблема:** Фраза "fixed population of vulnerable paths" может быть интерпретирована как слишком сильное утверждение.
**Решение:** Смягчить до "structurally constrained population of marginally viable paths."

#### 8.3.2 15m MUF ceiling interpretation
**Проблема:** Коэффициент 0.42× для 15m baseline invariance требует ювелирной формулировки.
**Решение:** Явно объяснить в §7.5, что storm depress MUF below 21 MHz для целых секторов, "выключая" трассу целиком.

#### 8.3.3 Day/night asymmetry non-replication
**Проблема:** Day/night эффект не воспроизвелся в held-out.
**Решение:** Признать это в Limitations, объяснить как intermittent auroral/PCA effects, требующие большего N.

---

## 9. РЕКОМЕНДАЦИИ ПЕРЕД SUBMISSION

### 9.1 Обязательные действия (MUST)

1. **🚨 Загрузить данные в Zenodo**
   ```bash
   # Сжать unified.parquet
   gzip data/processed/unified.parquet
   # Загрузить на Zenodo, получить DOI
   # Добавить в Data Availability:
   # "The unified dataset is archived at Zenodo: DOI:10.5281/zenodo.XXXXXXX"
   ```

2. **📝 Добавить CRediT statement**
   ```
   Author Contributions:
   A.P.: Conceptualization, Methodology, Software, Formal Analysis, 
         Writing—Original Draft, Supervision.
   M.P.: Data Curation, Software, Validation, Visualization, 
         Writing—Review & Editing.
   ```

3. **⚠️ Parameterize periods**
   ```python
   # В perm_test_18mo_3band.py заменить:
   full = df[(df['timestamp_utc'] >= '2024-04-01') & ...]
   # На:
   START_DATE = os.getenv('CROSSCORR_START', '2024-04-01')
   END_DATE = os.getenv('CROSSCORR_END', '2025-10-01')
   ```

### 9.2 Желательные действия (SHOULD)

4. **📊 Повысить coverage threshold**
   ```yaml
   # В .github/workflows/ci.yml:
   --cov-fail-under=70  # вместо 45
   ```

5. **🔬 Добавить spatial analysis в Future Work**
   ```
   Future work will incorporate Great Circle path geometry to resolve 
   spatial dependencies (e.g., polar cap absorption vs. mid-latitude 
   MUF depression) masked by global spot aggregation.
   ```

6. **📈 Явно признать small N в held-out**
   ```
   The held-out period (Jan-Mar 2026) contains only N=23 storm hours, 
   limiting statistical power for fine-grained replication. However, 
   the direction and magnitude of the primary effect (all 3 bands negative) 
   and the scale-dependence (Kp≥6 → -42.8%) are robustly replicated.
   ```

### 9.3 Опциональные улучшения (NICE-TO-HAVE)

7. **🎨 Улучшить визуализацию**
   - Добавить 95% CI error bars на все графики (уже сделано в v13)
   - Использовать colorblind-friendly палитры (viridis, cmocean)

8. **📚 Расширить references**
   - Добавить 2-3 недавних (2024-2025) работы по WSPR/HamSCI
   - Добавить ссылку на IAGA Kp index documentation

9. **🔧 Code quality**
   - Добавить docstrings к публичным функциям (если нет)
   - Удалить experimental modules из main branch

---

## 10. ФИНАЛЬНЫЙ ВЕРДИКТ

### 10.1 Готовность к arXiv: ✅ **ГОТОВО**
Проект представляет собой зрелый, хорошо документированный, воспроизводимый научный артефакт. Можно загружать **СЕГОДНЯ**.

### 10.2 Готовность к Space Weather: ⚠️ **ГОТОВО ПРИ УСЛОВИИ**
Статья находится на уровне Q1/Q2 журнала. После выполнения **3 обязательных действий** (Zenodo, CRediT, parameterize) — готова к submission.

### 10.3 Оценка по шкале Reviewer 2

| Критерий | Оценка | Комментарий |
|---|---|---|
| **Originality** | 8/10 | Baseline invariance — novel finding |
| **Significance** | 7/10 | Citizen science validation of ionospheric storms |
| **Rigor** | 9/10 | Block permutation, FDR, held-out, negative controls |
| **Reproducibility** | 9/10* | *При условии загрузки данных в Zenodo |
| **Clarity** | 8/10 | Well-structured, but some overclaiming |
| **References** | 7/10 | Comprehensive, but could add 2-3 recent papers |

**Overall score: 8.0/10** — **Accept with minor revisions**

---

## 11. ЗАКЛЮЧЕНИЕ

Это **впечатляющий проект**, демонстрирующий:
- Профессиональный уровень инженерии (291 test, CI/CD, type hints)
- Строгую методологию (block permutation, FDR, held-out)
- Беспрецедентную прозрачность (15+ аудитов, AI disclosure)
- Научную новизну (baseline invariance, scale-dependence)

Тот факт, что это семейный проект с 13-летним соавтором, делает его еще более впечатляющим. Однако **научный стандарт остается неизменным**: данные должны быть доступны, утверждения — обоснованы, ограничения — признаны.

После выполнения 3 обязательных действий (Zenodo, CRediT, parameterize) проект будет готов к submission в Space Weather с высокими шансами на принятие.

**Вердикт: Submit после 2-3 часов финальной полировки.**