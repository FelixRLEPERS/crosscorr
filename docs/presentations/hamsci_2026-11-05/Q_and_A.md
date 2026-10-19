# Q&A — HamSCI Science Telecon, 5 November 2026

Ответы на 10 типичных вопросов. EN — как ответить вслух,
RU — смысл и подводные камни. Все числа — из paper/main.tex (v1.3.1).

---

## Q1. Why a block permutation test instead of a GLM?

### EN
Spot counts are non-Gaussian, autocorrelated, and heteroscedastic —
a GLM would force distributional assumptions we cannot validate at
hourly resolution. The block permutation test makes almost no
assumptions: we compute residuals against a month, hour-of-day,
day-of-week baseline, then shuffle blocks of twenty-four consecutive
three-hour epochs (seventy-two hours — three full diurnal cycles,
longer than the mean storm duration of about nine hours) of the
residual series, while the observed Kp sequence stays fixed.
Shuffling residuals rather than storm labels preserves the
autocorrelation structure under the null without pretending that
geomagnetic activity is exchangeable in time. The held-out p-values
come from the same residual block permutation procedure.

### RU
Ключевая мысль: пермутация не требует нормальности, и тасуем мы
блоки остатков, а не метки Kp — геомагнитная активность физически
не перемешивается во времени. Остатки считаются от baseline
month × hour-of-day × day-of-week. Блок 72 ч намеренно длиннее
типичной бури (~9 ч), чтобы сохранить автокорреляцию. Если
спросят "а что, GLM нельзя?" — можно, но с теми же блоковыми
поправками; пермутация просто честнее.

---

## Q2. Why not spatially stratified analysis — by path or region?

### EN
Aggregating globally is a deliberate first-pass choice, and it is
our main limitation. Polar-cap paths and mid-latitude paths respond
differently — we say so in the paper. The next step is per-path
analysis using great-circle geometry; that work is planned but not
in this study.

### RU
Не оправдываться. Отвечать: "yes, that is limitation number four
in our list; the path-level analysis is our next paper".

---

## Q3. Is absolute loss (spots per hour) a meaningful metric?

### EN
Percentage drops are normalized by the quiet-time baseline, making
them stable as the network grows. Absolute loss is not strictly
invariant. The updated held-out point estimate (ratio 1.44) is larger
than the training estimate, but the held-out CI overlaps the training
CI. It is broadly consistent with proportional scaling with the
growing network (+35% baseline), but not a formal test of equality.
Percentage drops remain the more stable metric. We report both;
absolute loss should be treated as descriptive and re-validated
periodically.

### RU
Это тот случай, когда наша же "неудачная" находка — наш актив.
Подчеркнуть: метрика физически осмысленная, но инвариантность
не установлена. Цитировать keypoints статьи.

---

## Q4. Could the drop be a receiver artifact rather than ionospheric?

### EN
Receiver count grew over the period — by thirty-five percent on
forty meters — which would, if anything, push counts up, not down.
The permutation test compares storm versus quiet epochs inside the
same eighteen-month window with the same network, so slow network
growth cancels. Per-transmitter normalisation was not possible:
transmitter metadata exists for only a tiny subsample, which we
disclose. The Dst-index replication with a different storm
classification supports the ionospheric reading.

### RU
Главный аргумент: внутри-оконное сравнение (шторм vs тихие эпохи
в одном и том же окне сеть). Рост сети не может объяснить
именно штормовое падение. Про metadata.tx — честно: "tiny
subsample, disclosed in the paper".

---

## Q5. On held-out 15 m the raw CI includes zero — is it really replicated?

### EN
Two different statistics answer two different questions. The raw
confidence interval for fifteen meters indeed crosses zero — we
disclose that. The residual block permutation test — the same
method as in training — gives p equals eight times ten to the minus
five, significant. The CI is wide because there are only forty-seven
storm epochs and fifteen meters has the smallest effect size and the
noisiest baseline. We state both numbers side by side in the paper
rather than choosing the flattering one.

### RU
Не путать: CI — на сырых значениях, p — на резидах. Оба числа в
статье рядом. Это не подтасовка, это честное раскрытие.

---

## Q6. Could sporadic-E explain the training 15 m drop?

### EN
Summer fifteen-meter spots can be partially sporadic-E propagation,
and we flag that in the limitations. Two observations argue against
Es as the driver: the storm effect is present in every season,
including winter when Es is largely absent; and the direction of
the Es bias for storm versus quiet epochs cannot be determined from
spot counts alone, so it cannot manufacture a consistent
thirty-eight percent reduction across eighteen months.

### RU
Слабое место, но защищаемое: эффект есть и зимой. Не уходить в
углублённую физику Es — ответ должен быть 20 секунд.

---

## Q7. Why Kp as the primary index and not Dst?

### EN
Kp is the operational standard — three-hourly, planetary, complete
since 1932 — and it defines the storm threshold everyone recognises.
We then repeated the analysis with Dst below minus fifty nanoTesla
as an independent classification; the primary effect survives on
all three bands, with per-band differences we report in section 4.1.
So Kp is the headline index, Dst is the cross-check.

### RU
Не говорить "Kp лучше". Говорить: Kp — операционный стандарт,
Dst — независимая проверка; результат устойчив к выбору индекса.

---

## Q8. Any operational or real-time application?

### EN
Potentially yes. Normalised WSPR spot density could serve as a
near-real-time proxy for storm-driven HF degradation, complementing
riometers. The caveat from our absolute-loss scaling result: percentage drops
are normalized by the quiet-time baseline and remain stable as the
network grows, whereas absolute deviations scale with network size.
An operational system should therefore track the quiet baseline
continuously, use the normalized (percentage) response as the
primary trigger, and re-validate absolute levels periodically.

### RU
Это мостик к HamSCI-практике. Тон приглашающий: "we would welcome
a working group on this".

---

## Q9. What is next?

### EN
Three things. First, the six-month held-out replication — we are
limited by wspr.live download throughput, not by analysis. Second,
per-path analysis with great-circle geometry to separate polar from
mid-latitude response. Third, more bands — thirty, seventeen, twelve
meters — to pin down the MUF-threshold shape. And of course, journal
submission after the arXiv endorsement arrives.

### RU
Коротко, по пунктам. Не обещать сроков, кроме "limited by download
throughput" — это конкретика, которая звучит убедительно.

---

## Q10. Why do you say "consistent with" mechanisms instead of claiming causation?

### EN
Because spot counts are an integral measure of a propagation path,
not a direct sounding of the D-region or the MUF. What we show is
that the joint pattern — frequency ordering, UT-window crossover,
non-linear Kp gradient — matches the predicted signature of MUF
reduction plus D-region absorption, and does not match the
alternatives we considered. Establishing causation needs direct
ionosonde and absorption measurements on the same paths; that is a
collaboration we would welcome.

### RU
Классическая научная скромность — и она правильная. Фраза-ключ:
"the joint pattern matches the predicted signature". Заканчивать
приглашением к коллаборации с ионосондами.

---

## Backup facts (если спросят цифры)

- Training: 18 months (Apr 2024 – Sep 2025), 39 456 WSPR hours.
- 4 349 epochs per band; 198 storm (Kp ≥ 5) vs 3 035 quiet.
- Drops: −27.7 / −27.2 / −38.7 % (20/40/15 m), all p = 2e-5.
- Scale: ~−18 % (Kp 5–6), ~−34 % (Kp 6–7), ~−53 % (Kp ≥ 7).
- UT-day 12–18 UTC / UT-night 0–6 UTC: 15 m −48.9 / −18.7; 40 m −20.7 / −30.2.
- Absolute 40 m: train −18 285 [−23 807, −12 930];
  initial held-out −18 304 (ratio 1.00);
  re-pull −26 287 [−37 144, −12 472] (ratio 1.44, 95% CI [0.65, 2.33]);
  expected ~1.35 from +35 % network growth.
- Held-out Jan–Mar 2026: N_storm = 47; −26.7 / −29.0 / −22.1 %;
  p = 2e-5 / 2e-4 / 8e-5.
- 198 storm epochs ≈ 58 independent episodes (N_eff).
- DOIs: version 10.5281/zenodo.23402384, concept 10.5281/zenodo.23285958.
- Code: github.com/FelixRLEPERS/crosscorr (tag v1.3.1).
