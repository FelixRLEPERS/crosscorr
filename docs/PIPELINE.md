# Pipeline: математическое описание

Документ описывает **математику** каждого шага анализа в CrossCorr.
Для каждого метода — формула, параметры по умолчанию, реализация.

---

## 1. Обозначения

- $x_i(t)$ — значение детектора $i$ в момент времени $t$ (residual после унификации).
- $\tau$ — временной лаг (в единицах дискретизации).
- $d_{ij}$ — расстояние между детекторами $i$ и $j$ (haversine, км).
- $\alpha$ — уровень значимости (по умолчанию 0.05).
- $n$ — число наблюдений.
- $N_{\text{eff}}$ — эффективный размер выборки (с учётом автокорреляции).

---

## 2. Унификация данных

Все источники приводятся к единой схеме:

$$
\text{timestamp\_utc}, \text{detector\_id}, \text{detector\_type}, \text{residual}, \text{meta}
$$

Ресемплинг к единой частоте (по умолчанию `1h`), усреднение по bucket:

$$
x_i(t) = \frac{1}{|B_t|} \sum_{s \in B_t} \text{residual}_i(s)
$$

**Реализация:** `crosscorr_lib/analysis/cross_correlation.py:build_wide_by_detector`.

---

## 3. Кросс-корреляция с лагами

Для каждой пары $(i, j)$ вычисляется Spearman-корреляция на всех лагах
$\tau \in [-L, +L]$, где $L$ = `max_lag` (по умолчанию 72 = 3 дня по часам):

$$
r_{ij}(\tau) = \rho_{\text{Spearman}}\bigl(x_i(t),\, x_j(t + \tau)\bigr)
$$

Знак лага:
- $\tau > 0$ — $x_j$ отстаёт от $x_i$;
- $\tau < 0$ — $x_i$ отстаёт от $x_j$.

Порог минимального числа наблюдений: $n_{\text{valid}} \geq 10$.

**Реализация:** `crosscorr_lib/analysis/cross_correlation.py:lagged_cross_correlation`.

---

## 4. Max-statistic null (главное)

### 4.1. Проблема

Наивный подход: взять p-value на лучшем лаге $\tau^* = \arg\max_\tau |r_{ij}(\tau)|$.
**Это неверно**, потому что мы перебрали $2L+1 = 145$ лагов.
Ожидаемое число ложных срабатываний при $\alpha = 0.05$:
$1 - 0.95^{145} \approx 99.8\%$ — почти гарантированно найдётся «значимый» лаг.

### 4.2. Решение: Max-statistic test

Тестируем гипотезу «нет связи ни на одном лаге». Статистика:

$$
T_{ij}^{\text{obs}} = \max_{\tau \in [-L, L]} \bigl| r_{ij}(\tau) \bigr|
$$

Нулевое распределение строится через **phase randomization** (см. §5):

$$
T_{ij}^{(b)} = \max_{\tau} \bigl| r_{ij}^{(b)}(\tau) \bigr|, \quad b = 1, \ldots, B
$$

p-value:

$$
p_{ij} = \frac{1 + \#\{b : T_{ij}^{(b)} \geq T_{ij}^{\text{obs}}\}}{1 + B}
$$

**Ключевое свойство:** поиск по лагам **внутри** нулевого распределения.
Это даёт корректный p-value **без Bonferroni-коррекции**. Bonferroni был бы **слишком консервативным** — он не учитывает, что соседние лаги коррелируют.

**Параметры:**
- $B = 200$ для быстрого скрининга;
- $B = 1000+$ для публикации.

**Реализация:** `crosscorr_lib/analysis/surrogate.py:max_lag_surrogate_pvalue`.

---

## 5. Phase randomization (surrogate)

Для ряда $y$ применяется **фазовый суррогат**: FFT → случайные фазы → IFFT.

$$
\tilde{y}(t) = \mathcal{F}^{-1}\!\left[\, \bigl|\mathcal{F}[y]\bigr| \cdot e^{i \varphi_{\text{rand}}} \,\right]
$$

где $\varphi_{\text{rand}} \sim \mathcal{U}(0, 2\pi)$ — случайные фазы.

**Ограничения:**
- Фаза DC ($k = 0$) фиксируется в **0** — сохраняет нулевое среднее.
- Фаза Nyquist ($k = N/2$ для чётной длины) фиксируется в **0** — сохраняет вещественность.

Это **не итеративный** (non-ITC) суррогат. Для строгих тестов можно перейти
к ITC (Schreiber & Schmitz, 2000), но для большинства задач достаточно.

**Реализация:** `crosscorr_lib/analysis/surrogate.py:phase_surrogate`.

---

## 6. FDR (Benjamini-Hochberg)

После получения p-values для всех пар применяется **BH-коррекция**:

$$
q_{(i)} = \min_{k \geq i} \left\{ \frac{n \cdot p_{(k)}}{k} \right\}
$$

где $p_{(1)} \leq p_{(2)} \leq \ldots \leq p_{(n)}$ — отсортированные p-values,
$n$ — число пар.

Отклоняем $H_{(i)}$ если $q_{(i)} \leq \alpha$.

**Для симметричной матрицы:** используется только верхний треугольник
$\text{triu}(P, k=1)$ — каждая пара учитывается **один раз**.

**Реализация:** `crosscorr_lib/analysis/surrogate.py:fdr_bh_q`.

---

## 7. Effective sample size (ESS)

### 7.1. Проблема

Обычный p-value предполагает **независимые** наблюдения. Для AR(1) с $\varphi = 0.7$
эффективный размер выборки падает в $\sim 5$ раз. p-value **завышает** значимость.

### 7.2. Решение

Интегрированное время автокорреляции:

$$
\tau_{\text{int}} = 1 + 2 \sum_{k=1}^{K} \rho(k)
$$

где $\rho(k)$ — выборочная автокорреляция на лаге $k$. Суммирование останавливается
при $|\rho(k)| < 1.96 / \sqrt{n}$ (порог Sokal).

Эффективный размер выборки:

$$
N_{\text{eff}} = \frac{N}{\max(\tau_{\text{int}}^{(x)}, \tau_{\text{int}}^{(y)})}
$$

Скорректированный t-тест:

$$
t = r \cdot \sqrt{N_{\text{eff}} - 2} / \sqrt{1 - r^2}, \quad p = 2 \cdot (1 - F_t(|t|;\, N_{\text{eff}} - 2))
$$

**Реализация:** `crosscorr_lib/analysis/effective_sample.py:correlation_pvalue_with_ess`.

**Флаг CLI:** `--use-ess` в `cross_correlation.py`.

---

## 8. Block bootstrap

Альтернатива phase randomization для **не-стационарных** рядов.

Идея: нарезать ряд на блоки длины $L$, перемешать блоки, сшить.

$$
\tilde{y}(t) = \bigl[\, y(s_1 : s_1 + L),\, y(s_2 : s_2 + L),\, \ldots \,\bigr]
$$

где $s_k \sim \mathcal{U}(0, n - L)$ — случайные стартовые позиции.

p-value:

$$
p = \frac{1 + \#\{b : |r^{(b)}| \geq |r_{\text{obs}}|\}}{1 + B}
$$

**Параметры:** $L = 24$ (1 день для часовых данных).

**Реализация:** `crosscorr_lib/analysis/block_bootstrap.py:block_bootstrap_pvalue`.

---

## 9. Physical confounders

Удаление вклада Kp, Dst, F10.7 через OLS. Для каждого детектора $i$:

$$
x_i(t) = \alpha_i + \beta_{i,1} \cdot \text{Kp}(t) + \beta_{i,2} \cdot \text{Dst}(t) + \beta_{i,3} \cdot \text{F10.7}(t) + \varepsilon_i(t)
$$

Residual $\varepsilon_i(t)$ — «очищенный» ряд, используется для дальнейшего анализа.

**Мультиколлинеарность:** Kp и Dst сильно коррелируют. Используется
псевдообратная матрица (Moore–Penrose) — устойчива к коллинеарности.

**Реализация:** `crosscorr_lib/analysis/confounders.py:remove_confounders`.

**Флаг CLI:** `--remove-confounders data/confounders.csv`.

---

## 10. ADF stationarity test

Проверка стационарности через расширенный тест Дики-Фуллера:

$$
\Delta x_t = \alpha + \beta t + \gamma x_{t-1} + \sum_{k=1}^{p} \delta_k \Delta x_{t-k} + \varepsilon_t
$$

Нулевая гипотеза $H_0$: $\gamma = 0$ (единичный корень, ряд **нестационарен**).

Если $p < 0.05$ — ряд **стационарен** (нет единичного корня).

**Автовыбор лагов:** `autolag="AIC"`.

**Реализация:** `crosscorr_lib/analysis/stationarity.py:adf_test`.

---

## 11. Distance-based analysis

Для каждой значимой пары $(i, j)$ — haversine-расстояние:

$$
d_{ij} = 2R \arcsin\!\sqrt{\sin^2\!\frac{\Delta\varphi}{2} + \cos\varphi_i \cos\varphi_j \sin^2\!\frac{\Delta\lambda}{2}}
$$

где $R = 6371$ км, $\varphi$ — широта, $\lambda$ — долгота.

Регрессия:

$$
r_{ij} = a + b \cdot d_{ij} + \epsilon_{ij}
$$

OLS: $\hat{b} = \frac{\sum (d_{ij} - \bar{d})(r_{ij} - \bar{r})}{\sum (d_{ij} - \bar{d})^2}$, R² = $1 - \text{SS}_{\text{res}} / \text{SS}_{\text{tot}}$.

**Гипотеза:** $b < 0$ (близкие детекторы коррелируют сильнее).

**Реализация:** `crosscorr_lib/analysis/distance_analysis.py`.

---

## 12. Порядок вызовов (рекомендуемый)

```bash
# 1. Унификация данных
python data/scripts/unify_schema.py

# 2. Проверка стационарности (ADF)
python -m crosscorr_lib.analysis.stationarity

# 3. Кросс-корреляция с max-stat + ESS
python -m crosscorr_lib.analysis.cross_correlation --use-max-stat --use-ess

# 4. Удаление конфаундеров (опционально)
python -m crosscorr_lib.analysis.cross_correlation --remove-confounders data/confounders.csv

# 5. Distance-based analysis
python -m crosscorr_lib.analysis.distance_analysis
```

Результаты: `results/*.csv`.

---

## 13. Ссылки

- Benjamini, Y., Hochberg, Y. (1995). *Controlling the FDR*. JRSS-B.
- Schreiber, T., Schmitz, A. (2000). *Surrogate time series*. Physica D, 142, 346–382.
- Sokal, A. (1996). *Monte Carlo Methods in Statistical Mechanics*. Springer.
- Kantelhardt, J. W. et al. (2002). *Multifractal detrended fluctuation analysis*. Physica A, 316, 87–114.
- Dickey, D. A., Fuller, W. A. (1979). *Distribution of the Estimators for Autoregressive Time Series*. JASA, 74, 427–431.