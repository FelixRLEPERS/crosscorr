# Speaker notes — HamSCI Science Telecon, 5 November 2026

Talk: "Scale-dependent WSPR response to geomagnetic storms".
Speaker: Alexey Petrov. Total speaking time: ~9–10 minutes.
Each slide block: EN — what to say (approximate wording),
RU — перевод и подсказки по подаче.

---

## Slide 1 — Title (~0:30)

### EN (say this)
Good [morning / afternoon], everyone — depending on your time zone.
Thank you for the invitation to this telecon. My name is Alexey Petrov.
This is joint work with my co-author and son, Makar Petrov; he is
thirteen, he built much of the analysis code, and he is watching
today but will not be speaking. We are independent researchers from
Russia. In the next ten minutes I will show how geomagnetic storms
affect the WSPR radio network — and why that network can be used as
a scientific instrument.

### RU (перевод и подсказки)
Поздороваться по времени суток у слушателей (ET). Представиться,
сразу честно представить Макара как соавтора и разработчика кода —
это вызывает уважение и задаёт тон. Не оправдываться, не извиняться.
Пауза. Переход: "Let me start with why we think WSPR matters."

---

## Slide 2 — Why WSPR? (~1:00)

### EN (say this)
WSPR — Weak Signal Propagation Reporter — is a very low rate digital
mode that amateur radio operators run continuously. When one station
hears another, that reception is uploaded to a public database: who
heard whom, when, on which band. Each such spot is an opportunistic
measurement of one HF propagation path. Thousands of operators do
this every hour, for free, around the world. In effect the community
has built a distributed ionospheric sensor: global, continuous, and
open. Our question was simple: when the geomagnetosphere is disturbed,
does this sensor see it? In other words — do storm conditions suppress
HF propagation, as reflected in spot counts?

### RU (перевод и подсказки)
Объяснить WSPR простым языком: "аматоры слушают друг друга и
загружают журналы". Ключевая метафора — "распределённый сенсор
ионосферы", повторить её: она пронизывает всю презентацию.
Жестом или словесно указать на картинку: "every line you see here is
a real measured link".

---

## Slide 3 — Data and method (~1:10)

### EN (say this)
We analysed eighteen months of data, from April 2024 to September
2025 — the window with complete hourly coverage for all three bands
on the wspr.live mirror. That is thirty-nine thousand WSPR hours.
We merged the hourly spot counts with the three-hourly Kp index from
GFZ Potsdam — a strict inner join on the epoch timestamps, no forward
filling. This gives about forty-three hundred epochs per band, of
which one hundred ninety-eight are storm epochs — Kp of five or
higher — and just over three thousand are quiet epochs, Kp below
three. Our primary statistic is a block permutation test: fifty
thousand iterations, a block of seventy-two hours — three full
diurnal cycles — with Benjamini–Hochberg false-discovery control.
As a robustness check we repeated the whole analysis with the Dst
index from Kyoto.

### RU (перевод и подсказки)
Не зачитывать все числа подряд — это убивает внимание. Говорить
крупные "жирные" числа: 18 месяцев, 198 штормовых эпох, 50 тысяч
итераций. Остальное — общий жест на график. Подчеркнуть методическую
честность: "no forward filling", "false-discovery control" — это
слова, которые аудитория-учёные ценит.

---

## Slide 4 — Result 1: frequency and scale dependence (~1:20)

### EN (say this)
This is the headline result. During storm epochs the spot density
drops by twenty-seven point seven percent on twenty meters, twenty-
seven point two on forty meters, and thirty-eight point seven on
fifteen meters. All three are significant at two times ten to the
minus five — the resolution floor of our permutation test. The right
panel shows the second part of the story: the effect is not linear
in storm intensity. At Kp five to six the drop is approximately 18
percent; at Kp six to seven, thirty-four; at Kp seven and above,
fifty-three. So severity matters, and it matters more than a linear
dose-response would suggest. The frequency ordering — fifteen meters
hit hardest — is what we would expect if storm-time MUF reduction
pushes the highest band below its normal propagation ceiling; the
similar drops on twenty and forty meters are consistent with
D-region absorption.

### RU (перевод и подсказки)
Это главный слайд — говорить медленно, сделать паузу после каждого
процента. Показывать пальцем на левую панель, потом на правую.
Формулировку "consistent with" держать в уме: mechanisms мы не
доказали, а показали совместимость (см. слайд Q&A).

---

## Slide 5 — Result 2: UT-window asymmetry (~1:10)

### EN (say this)
We then asked whether the time of day matters. We split storm epochs
into UT-day — twelve to eighteen UTC — and UT-night — zero to six
UTC. In the UT-day window, fifteen meters drops almost half: minus
forty-eight point nine percent; in the UT-night window its effect
shrinks to minus eighteen. Forty meters shows the opposite: in the
UT-night window it drops minus thirty, more than the minus twenty-
one of the UT-day window. This crossover is the fingerprint of two
different physical mechanisms. The solar D-layer, which causes
absorption in UT-day hours, disappears minutes after sunset; what
remains in the UT-night window is absorption from energetic particle
precipitation — auroral and polar-cap — which scales as one over f
squared, so it hurts forty meters more than twenty. Two caveats we
state explicitly: these are UT windows, not simultaneous local
day and night for a global network; and this asymmetry is a
training-period result — the three-month held-out window has too
few storms to test it independently.

### RU (перевод и подсказки)
"Кроссовер" — ключевое слово: в UT-день 15 м хуже всего, в UT-ночь — 40 м.
Объяснить "one over f squared" жестом: поглощение сильнее на низких
частотах. Обязательно произнести оба caveat: (1) это UT-окна, а не
одновременные локальные день/ночь в глобальной сети; (2) это результат
тренировочного периода — held-out его не проверяет. Иначе вопрос
"а насколько это устойчиво?" придётся отвечать без подготовки.

---

## Slide 6 — Result 3: absolute loss on 40 m (~1:30)

### EN (say this)
The third question: is the absolute loss — spots per hour — a stable
physical quantity, even as the network grows? In the training period
the answer looked yes. The loss on forty meters was minus eighteen
thousand two hundred eighty-five spots per hour. The first archived
held-out snapshot gave minus eighteen thousand three hundred four —
a ratio of one point zero zero. That was an attractive result. But
the wspr.live database keeps growing as operators upload logs with
a lag. So we re-downloaded the same three months in October 2026 —
and the loss came out minus twenty-six thousand two hundred
eighty-seven: ratio one point four four, with a wide bootstrap
interval from zero point six five to two point three three. That
interval is wide enough to include both perfect invariance and
proportional scaling. But the network had grown by thirty-five
percent in the meantime, and if the percentage drop stayed constant
we would expect a ratio of about one point three five — close to
where our point estimate sits. The honest summary: absolute loss
scales roughly with the network, while percentage drops remain the
more stable metric. This slide is deliberately in our paper's key
points — we prefer to state the correction ourselves.

### RU (перевод и подсказки)
Это самый "взрослый" слайд — история об ошибке, которую мы поймали
и честно показали. Не извиняться, а говорить уверенно: наука так и
работает. Подчеркнуть: "we report it ourselves" — доверие аудитории
растёт. Numbers: 18 285 / 18 304 / 26 287 / ratio 1.44 (CI 0.65–2.33) / expected 1.35 / +35%.

---

## Slide 7 — Held-out replication (~1:00)

### EN (say this)
So what does replicate? The relative effect — robustly. On the
independent held-out window, January to March 2026, we have forty-
seven storm epochs per band. The drops are minus twenty-six point
seven percent on twenty meters, minus twenty-nine point zero on
forty meters, and minus twenty-two point one on fifteen meters.
All three are significant under the residual permutation test — at or
below two times ten to the minus four; on fifteen meters the raw
confidence interval still includes zero.
And when we match by storm strength — the Kp six to seven bin —
the held-out drops agree with the training values to within one to
twelve percent. We use this window strictly as a confirmation set:
its purpose is to confirm direction and magnitude, not to discover
new effects.

### RU (перевод и подсказки)
Кратко и уверенно. Таблица на экране говорит сама за себя — не
зачитывать каждую строку, выделить только: "all three significant".
Фраза "confirmation set, not a discovery set" — запомнить и повторить
дословно, она отсекает вопрос о p-hacking.

---

## Slide 8 — Limitations (~1:00)

### EN (say this)
Our limitations are honest and we list them in the paper. Eighteen
months is not a climatology — the window sits in a solar-maximum
phase. The held-out period has only forty-seven storm epochs, so
secondary effects like the UT-window asymmetry are not independently
tested there; on fifteen meters the raw confidence interval still
includes zero, even though the residual-based permutation test is
significant. We aggregate globally, which masks regional structure —
polar paths versus mid-latitude paths — and per-path geometry is
future work. Our UT windows are not simultaneous local day and night
across a global network; also, the spot counts conflate propagation
with station activity — we cannot normalise by active transmitters.
F10.7 enters only as monthly means. And the one hundred
ninety-eight storm epochs are not independent: grouped into episodes
they amount to about fifty-eight distinct events.

### RU (перевод и подсказки)
Говорить спокойно и коротко: список оговорок не читать весь —
перечислить 3–4, остальное "in the paper". Тон: "we know the
boundaries of our claim". Это разоружает заранее.

---

## Slide 9 — Conclusions (~1:00)

### EN (say this)
To conclude, in five sentences. One: geomagnetic storms cut WSPR
spot density by twenty-seven to thirty-nine percent on all three
bands, at two times ten to the minus five. Two: the effect is
scale-dependent — minus eighteen, minus thirty-four, minus fifty-
three percent as Kp increases. Three: it replicates in direction on the
held-out window on all three bands, under the residual permutation
test. Four: absolute loss scales roughly with network growth — ratio
one point four four, close to the one point three five expected from
the thirty-five percent baseline growth; percentage drops remain the
more stable metric.
Five: the pattern is consistent with two mechanisms — MUF reduction
on fifteen meters and D-region absorption on twenty and forty.
Bottom line: WSPR is a viable distributed ionospheric sensor for
storm-driven HF degradation — and we think HamSCI can use it.

### RU (перевод и подсказки)
Пять пунктов — держать ритм, не спешить. Последнюю фразу связать
с аудиторией: "and we think HamSCI can use it" — это приглашение
к сотрудничеству, уместное на HamSCI-телеконе.

---

## Slide 10 — Questions (~0:20)

### EN (say this)
Thank you very much. The full paper is on Zenodo under the version
DOI you see on the slide; the code and data are on GitHub. I am
happy to take questions — and Makar is in the chat as well, so if
there are code questions, he can type answers there.

### RU (перевод и подсказки)
Поблагодарить. Указать на DOI. Упомянуть, что Макар в чате — это
мило и эффективно: соавтор реально присутствует.

---

## Timing summary

| Slide | Time | Cumulative |
|---|---|---|
| 1 | 0:30 | 0:30 |
| 2 | 1:00 | 1:30 |
| 3 | 1:10 | 2:40 |
| 4 | 1:20 | 4:00 |
| 5 | 1:10 | 5:10 |
| 6 | 1:30 | 6:40 |
| 7 | 1:00 | 7:40 |
| 8 | 1:00 | 8:40 |
| 9 | 1:00 | 9:40 |
| 10 | 0:20 | 10:00 |

Запас на паузы и переходы: ~30–60 с. Если время давят — сократить
слайд 8 до трёх пунктов и слайд 2 до 40 секунд.

## Rehearsal checklist

- Прогнать вслух 3 раза; второй раз — по таймеру.
- Проверить, что все цифры произносятся уверенно (особенно слайд 6).
- Подготовить экран: PDF открыть заранее, второе окно — chat.
- Проверить заранее, что слушатели видят экран (тестовый screen-share).
- Макар: держать рядом Q_and_A.md и отвечать в чате на вопросы по коду.
