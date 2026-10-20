# Q&A — HamSCI Science Telecon, 5 November 2026

Ответы на 11 типичных вопросов. EN — как ответить вслух,
RU — смысл и подводные камни. Все числа — из paper/main.tex (round-3
revision).

## Number policy — raw vs adjusted

Main talk and slides use **raw** drops: training −27.7 / −27.2 / −38.7 %;
held-out −26.7 / −29.0 / −22.1 %. If asked about confounders:
“We also computed adjusted drops accounting for month/hour/DOW,
which are -33.6% / -27.1% / -39.8% — the effect holds strongly.”
Held-out adjusted: −19.1 / −21.2 / −23.4 % (CIs exclude zero;
directional, smaller than training). See Q1, Q5, Q11.

---

## Q1. Why a block permutation test, and how does the GLM fit in?

### EN
We use both, for different purposes. The block permutation test is the
primary inference: it makes almost no distributional assumptions and
shuffles 72-hour blocks of residuals against a month, hour-of-day,
day-of-week baseline while the observed Kp sequence stays fixed.
The negative-binomial GLM with month, UT-hour and day-of-week fixed
effects estimates covariate-adjusted drops and episode-clustered
confidence intervals; it is not the primary test. The two agree in
sign and significance. For 20 m the adjusted drop is larger because
storm epochs are over-represented at 00 UTC and in June 2025, when the
20 m quiet baseline is higher than average. So the permutation p-value
is the confirmatory test, and the GLM quantifies the effect after
removing the observed imbalance.

### RU
Ключевая мысль: пермутация — основной тест, GLM — оценка эффекта
с поправкой на дисбаланс. Раньше в ответе было "GLM не нужен";
теперь он есть, поэтому нельзя говорить, что мы его отвергаем.
Подчеркнуть: оба метода дают тот же знак и значимость; для 20 м
adjusted сильнее из-за июня 2025 и 00 UTC.

---

## Q2. Why not spatially stratified analysis — by path or region?

### EN
Aggregating globally was the first pass and remains a limitation. In
this revision we add a coarse distance-binned analysis (0–2 000,
2 000–5 000, 5 000–10 000, above 10 000 km). The strongest drop is on
5 000–10 000 km paths on all three bands, but these bins are a proxy:
they do not resolve latitude, local solar time, or individual
transmitter–receiver paths. Full path-level geometry is the next step.

### RU
Не оправдываться. Отвечать: "global aggregation — first pass; now we
have distance bins as a first step; latitude/LST/path geometry is next".
Не говорить, что per-path анализа нет совсем — он есть, но грубый.

---

## Q3. Is absolute loss (spots per hour) a meaningful metric?

### EN
Percentage drops are normalized by the quiet-time baseline, making
them stable as the network grows. Absolute loss is not strictly
invariant. The updated held-out point estimate (ratio 1.44) is larger
than the training estimate, but the held-out CI overlaps the training
CI. It is broadly consistent with proportional scaling with the
growing network (+35% baseline), but not a formal test of equality.
The ratio interval also includes unity, so invariance cannot be
excluded either. Percentage drops remain the more stable metric. We
report both; absolute loss should be treated as descriptive and
re-validated periodically.

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
rather than choosing the flattering one. For completeness: after
month/hour/DOW adjustment the held-out drops are −19.1 / −21.2 /
−23.4 %, all CIs exclude zero; they are smaller than training, which
is why we call the replication directional rather than exact.

### RU
Не путать: CI — на сырых значениях, p — на резидах. Оба числа в
статье рядом. Это не подтасовка, это честное раскрытие.

---

## Q6. Could sporadic-E explain the training 15 m drop?

### EN
Summer fifteen-meter spots can be partially sporadic-E propagation,
and we flag that in the limitations. We now have a seasonal check:
the 15 m drop is present in every season (−45.7 % DJF, −32.9 % MAM,
−33.4 % JJA, −44.2 % SON), and excluding all summer epochs leaves
−41.3 % (95 % CI [−48.7, −33.1]). So summer Es cannot manufacture
the effect. The DJF estimate rests on only 14 storm epochs, so the
seasonal numbers are descriptive.

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
riometers. The caveat from our absolute-loss result: percentage drops
are normalized by the quiet-time baseline and remain stable as the
network grows, whereas absolute deviations may scale with network size.
An operational system should therefore track the quiet baseline
continuously, use the normalized (percentage) response as the
primary trigger, and re-validate absolute levels periodically.

### RU
Это мостик к HamSCI-практике. Тон приглашающий: "we would welcome
a working group on this".

---

## Q9. What is next?

### EN
Three things. First, a longer held-out window — we are limited by
wspr.live download throughput, not by analysis. Second, per-path
analysis with transmitter/receiver coordinates and local solar time;
the distance bins are a first step. Third, more bands — thirty,
seventeen, twelve meters — to pin down the MUF-threshold shape. And
of course, journal submission after the arXiv endorsement arrives.

### RU
Коротко, по пунктам. Не обещать сроков, кроме "limited by download
throughput" — это конкретика, которая звучит убедительно.

---

## Q10. Why do you say "consistent with" mechanisms instead of claiming causation?

### EN
Because spot counts are an integral measure of a propagation path,
not a direct sounding of the D-region or the MUF. What we show is
that the joint pattern — frequency ordering, UT-window crossover,
non-linear Kp gradient — is more consistent with MUF reduction plus
D-region absorption than with the alternatives we considered. The
survivor-SNR near-invariance adds that the count loss is dominated by
marginal paths disappearing, not by uniform degradation. But this is
not a unique signature: establishing causation needs direct ionosonde
and absorption measurements on the same paths; that is a collaboration
we would welcome.

### RU
Классическая научная скромность — и она правильная. Фраза-ключ:
"the joint pattern matches the predicted signature". Заканчивать
приглашением к коллаборации с ионосондами.

---

## Q11. Why is the adjusted 20 m drop larger than the raw one?

### EN
Because storm epochs are not evenly distributed over the 18 months.
June 2025 contributes 16.7 % of the storm sample but only 4.6 % of the
quiet sample, and the 00 UTC hour contributes 17.7 % versus 11.6 %.
The 20 m quiet baseline is higher in June and at 00 UTC, so the raw
storm-minus-quiet comparison understates the effect. The
negative-binomial model with month, UT-hour and day-of-week controls
raises the 20 m estimate from −27.7 % to −33.6 %. The 40 m estimate is
essentially unchanged (−27.2 % to −27.1 %), and 15 m moves only
slightly (−38.7 % to −39.8 %). That is why we report both raw and
adjusted values and treat the raw 20 m number as conservative.

### RU
Это ответ на самый вероятный вопрос после доклада: "почему цифры
разные?". Не прятать: показать дисбаланс (июнь 2025, 00 UTC) и
объяснить, что adjusted — не "лучшая" цифра, а оценка после
контроля. Для 40 м разницы нет — это хороший знак устойчивости.

---

## Backup facts (если спросят цифры)

- Training: 18 months (Apr 2024 – Sep 2025), 39 456 WSPR hours.
- 4 349 epochs per band; 198 storm (Kp ≥ 5) vs 3 035 quiet.
- Raw drops: −27.7 / −27.2 / −38.7 % (20/40/15 m), all p ≤ 2e-5.
- Adjusted drops: −33.6 [−39.9, −26.7] / −27.1 [−33.2, −20.5] /
  −39.8 [−46.8, −31.8] %.
- Scale: ~−18 % (Kp 5–6), ~−34 % (Kp 6–7), ~−53 % (Kp ≥ 7);
  trend p = 8e-4 / ≤2e-4 / 0.020; highest bin = 38 epochs, 12 episodes.
- UT-day 12–18 UTC / UT-night 0–6 UTC: 15 m −48.9 / −18.7;
  40 m −20.7 / −30.2.
- SNR of decoded spots, adjusted storm−quiet: +0.25 [0.11, 0.38] dB
  (15 m), −0.22 [−0.36, −0.07] (20 m), −0.41 [−0.56, −0.26] (40 m).
- Distance-resolved drop, 5–10 Mm bin: −60.8 / −53.5 / −56.0 %
  (20/40/15 m); long-path bins are 3–13 % of storm spots.
- Absolute 40 m: train −18 285 [−23 807, −12 930];
  initial held-out −18 304 (ratio 1.00);
  re-pull −26 287 [−37 144, −12 472] (ratio 1.44, 95% CI [0.65, 2.33]);
  expected ~1.35 from +35 % network growth.
- Held-out Jan–Mar 2026: N_storm = 47, N_quiet = 439;
  raw −26.7 / −29.0 / −22.1 %; adjusted −19.1 / −21.2 / −23.4 %;
  p ≤ 2e-5 / 2e-4 / 8e-5. Raw 95% CIs: 20 m [−41.5, −3.4],
  40 m [−40.8, −14.0], 15 m [−42.5, 22.8] %.
- 198 storm epochs ≈ 58 independent episodes (N_eff).
- DOIs: version 10.5281/zenodo.23402384, concept 10.5281/zenodo.23285958.
- Code: github.com/FelixRLEPERS/crosscorr (core tag v1.3.1;
  round-3 scripts at the revision accompanying the manuscript).
