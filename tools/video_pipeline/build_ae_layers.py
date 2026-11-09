"""Build slides_ru_layers.tex (AE variant A) from slides_ru.tex.

Verify -> apply: read source, splice by exact 1-based line spans, write LF/UTF-8.
Only preamble blocks are transcribed anew; frame bodies come verbatim from source.
"""

import re

SRC = r"G:\crosscorr\docs\presentations\school_ru\slides_ru.tex"
DST = r"G:\crosscorr\docs\presentations\school_ru\slides_ru_layers.tex"

with open(SRC, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")  # LF file
assert len(lines) == 375, len(lines)  # 374 lines + trailing '' from final \n


# --- sanity: expected anchors at expected lines -------------------------
def L(n):
    return lines[n - 1]


assert L(59).startswith("  \\setbeamertemplate{footline}"), L(59)
assert L(64) == "      \\hskip1.1cm}\\vskip3mm}", L(64)
assert L(75).startswith("\\newcommand{\\hud}[1]"), L(75)
assert L(101).strip() == "\\end{tikzpicture}}", L(101)
assert L(105).startswith("\\newcommand{\\slidetitle}[2]"), L(105)
assert L(116).strip() == "\\end{tikzpicture}}", L(116)
assert L(138).startswith("\\newcommand{\\setbg}[2]"), L(138)
assert L(150).startswith("\\newcommand{\\setflatbg}"), L(150)
assert L(162) == "\\begin{document}", L(162)
assert L(269).strip().startswith("\\node[statbox,minimum height=2.1cm] (a)"), L(269)
assert L(274).strip().startswith("{\\small\\color{dim}Сигналов"), L(274)
assert L(289).strip().startswith("{\\codefont\\scriptsize\\color{dim}P-VALUE"), L(289)

# --- replacement blocks --------------------------------------------------
FOOTLINE = r"""  \setbeamertemplate{footline}{%
    \ifx\AEmodesel\AEcapC
      \ifx\AEchromesel\AEcfoot
        \hbox to \paperwidth{\hskip1.1cm
          \raisebox{0pt}[0pt][0pt]{\includegraphics[height=0.40cm]{figures/logo-square-ru-dark.png}}%
          \hfil{\color{dim}\codefont\scriptsize SPACE WEATHER // 2026SW005535}%
          \hfil\vphantom{\color{dim}\codefont\scriptsize\insertframenumber\,/\,\inserttotalframenumber}%
          \hskip1.1cm}\vskip3mm
      \fi
      \ifx\AEchromesel\AEconair
        \hbox to \paperwidth{\hfil{\color{dim}\codefont\scriptsize\insertframenumber\,/\,\inserttotalframenumber}\hskip1.1cm}\vskip3mm
      \fi
    \else
      %% mode L (контент-слой): футлайн скрыт, но сохраняем его вертикальный
      %% отпечаток (hbox + vskip3mm), иначе beamer смещает контент на ~24px.
      \vphantom{\hbox to \paperwidth{\hskip1.1cm
          \raise\boxed{0pt}[0pt][0pt]{\includegraphics[height=0.40cm]{figures/logo-square-ru-dark.png}}%
          \hfil{\color{dim}\codefont\scriptsize SPACE WEATHER // 2026SW005535}%
          \hfil{\color{dim}\codefont\scriptsize00/08}%
          \hskip1.1cm}}\vskip3mm
    \fi
  }"""

HUD = r"""\newcommand{\hud}[1]{%
  \ifx\AEmodesel\AEcapC
    \ifx\AEchromesel\AEchud
      \begin{tikzpicture}[remember picture,overlay]
        %% верхние уголки
        \draw[cyan,line width=0.6pt] ([xshift=0.4cm,yshift=-0.4cm]current page.north west)
            -- ([xshift=1.4cm,yshift=-0.4cm]current page.north west)
            ([xshift=0.4cm,yshift=-0.4cm]current page.north west)
            -- ([xshift=0.4cm,yshift=-1.4cm]current page.north west);
        \draw[amber,line width=0.6pt] ([xshift=-0.4cm,yshift=-0.4cm]current page.north east)
            -- ([xshift=-1.4cm,yshift=-0.4cm]current page.north east)
            ([xshift=-0.4cm,yshift=-0.4cm]current page.north east)
            -- ([xshift=-0.4cm,yshift=-1.4cm]current page.north east);
        %% нижние уголки
        \draw[amber,line width=0.6pt] ([xshift=0.4cm,yshift=0.4cm]current page.south west)
            -- ([xshift=1.0cm,yshift=0.4cm]current page.south west)
            ([xshift=0.4cm,yshift=0.4cm]current page.south west)
            -- ([xshift=0.4cm,yshift=1.0cm]current page.south west);
        \draw[cyan,line width=0.6pt] ([xshift=-0.4cm,yshift=0.4cm]current page.south east)
            -- ([xshift=-1.0cm,yshift=0.4cm]current page.south east)
            ([xshift=-0.4cm,yshift=0.4cm]current page.south east)
            -- ([xshift=-0.4cm,yshift=1.0cm]current page.south east);
        %% статус-бар (статичная часть; номер -- в отдельном слое onair)
        \node[anchor=north west,text=dim,font=\codefont\scriptsize]
            at ([xshift=1.7cm,yshift=-0.42cm]current page.north west) {CROSSCORR v1.6.4};
        \node[anchor=north east,text=dim,font=\codefont\scriptsize]
            at ([xshift=-1.7cm,yshift=-0.42cm]current page.north east)
            {\textcolor{amber}{\textbullet} ON AIR\ \ \vphantom{{\textcolor{cyan}{#1}/08}}};
      \end{tikzpicture}%
    \fi
    \ifx\AEchromesel\AEconair
      \begin{tikzpicture}[remember picture,overlay]
        \node[anchor=north east,text=dim,font=\codefont\scriptsize]
            at ([xshift=-1.7cm,yshift=-0.42cm]current page.north east)
            {{\textcolor{cyan}{#1}/08}};
      \end{tikzpicture}%
    \fi
  \fi}"""

SLIDETITLE = r"""\newcommand{\slidetitle}[2]{%
  \vspace{1.55cm}%
  \AElayer{\AEcur}{title}{%
  \begin{tikzpicture}[remember picture,overlay]
    \node[anchor=north west,align=left]
        at ([xshift=1.1cm,yshift=-0.92cm]current page.north west){%
      {\codefont\scriptsize\color{cyan}#1}\\[3pt]
      {\techfont\scaledfs{17.28}{22}\bfseries\color{txt}#2}};
    \fill[cyan] ([xshift=1.1cm,yshift=-2.20cm]current page.north west)
        rectangle ([xshift=3.4cm,yshift=-2.235cm]current page.north west);
    \fill[amber] ([xshift=3.55cm,yshift=-2.20cm]current page.north west)
        rectangle ([xshift=4.05cm,yshift=-2.235cm]current page.north west);
  \end{tikzpicture}}}"""

SETBG = r"""%% AE: фоны НЕ рендерим -- слой должен лежать на 100% прозрачном фоне
\newcommand{\setbg}[2]{}
\newcommand{\setflatbg}{}
%% бимер заливает background canvas ЦВЕТОМ по умолчанию (проверено: сплошной
%% #0b1220, alpha0=0%) -- шаблоны канвы должны быть пустыми:
\setbeamertemplate{background}{}
\setbeamertemplate{background canvas}{}"""

MACROS = r"""%% ==================== AE LAYERS (Phase 2, variant A) ====================
%% Экспорт прозрачных слоёв для After Effects. РОВНО ОДНА активная строка-режим ниже.
\def\AEmodesel{}        % 'L' = слой, 'C' = хром (HUD/футлайн/номера), '' = ничего
\def\AEslidesel{}       % слайд выбранного слоя
\def\AElayersel{}       % id выбранного слоя
\def\AEchromesel{}      % какой хром: hud-frame | footline-frame | onair
\def\AEcur{0}           % номер текущего слайда (вставляется в каждом frame)
\def\AEcapL{L}
\def\AEcapC{C}
\def\AEchud{hud-frame}
\def\AEcfoot{footline-frame}
\def\AEconair{onair}
%% видимость узлов стат-ряда слайда 5 (текст/заливка/контур отдельно: стиль
%% statbox задаёт fill opacity=0.62 и text opacity=1 ПОСЛЕ моих ключей не
%% перекрыть нельзя -- ключи идут в ХВОСТЕ опций и перекрывают стиль).
%% Узел скрыт = 0/0/0 (100% alpha0, но геометрию right=... of ... держит).
%% Макросы ТОЛЬКО в значениях: запятая внутри макроса ломает pgfkeys (проверено).
\def\AEaf{0}\def\AEat{0}\def\AEad{0}
\def\AEbf{0}\def\AEbt{0}\def\AEbd{0}
\def\AEcf{0}\def\AEct{0}\def\AEcd{0}
\def\AEidsa{stat-20m}
\def\AEidsb{stat-40m}
\def\AEidsc{stat-15m}
\newif\ifAEcontent      % контент кадров рендерится только в режиме слоя
%% \AEbody{...} -- гейт тела кадра. ВАЖНО: условие ТОЛЬКО внутри макроса!
%% Прямой \if...\begin{env}...\end{env}\fi в теле beamer-кадра ломается
%% ("Incomplete \ifx"), а макрос-обёртка -- работает (проверено t18/t25).
%% \AEonly{<слайд>}{<id>}: на слайде <слайд> рендерится ТОЛЬКО слой <id>.
%% Невыбранные слои гасятся \vphantom: ноль ширины, высота строки сохраняется
%% -> геометрия последующих блоков 1:1 как в деке (важно для позиционирования).
%% ВАЖНО про \node: тикз-\node НЕЛЬЗЯ оборачивать в макрос/условие
%% ("A node must have a (possibly empty) label text", проверено tnode4/5) --
%% узлы остаются ПРЯМЫМИ, видимость = хвостовые ключи со значениями-макросами.
\newcommand{\AEonly}[2]{%
  \def\AEmodesel{L}\def\AEslidesel{#1}\def\AElayersel{#2}\AEcontenttrue
  \def\AEaf{0}\def\AEat{0}\def\AEad{0}%
  \def\AEbf{0}\def\AEbt{0}\def\AEbd{0}%
  \def\AEcf{0}\def\AEct{0}\def\AEcd{0}%
  \def\AEtmpa{#2}%
  \ifx\AEtmpa\AEidsa \def\AEaf{0.62}\def\AEat{1}\def\AEad{1}\fi
  \ifx\AEtmpa\AEidsb \def\AEbf{0.62}\def\AEbt{1}\def\AEbd{1}\fi
  \ifx\AEtmpa\AEidsc \def\AEcf{0.62}\def\AEct{1}\def\AEcd{1}\fi}
%% \AEchrome{hud-frame|footline-frame|onair}: только хром, контент кадров скрыт
\newcommand{\AEchrome}[1]{\def\AEmodesel{C}\def\AEchromesel{#1}\AEcontentfalse}
\long\def\AEbody#1{\ifAEcontent #1\fi}
\newcommand{\AElayer}[3]{%
  \ifx\AEmodesel\AEcapL
    \edef\AEtmpa{#1}\edef\AEtmpb{#2}%
    \ifx\AEtmpa\AEslidesel
      \ifx\AEtmpb\AElayersel #3\else\vphantom{#3}\fi
    \else\vphantom{#3}\fi
  \fi}
\AEcontentfalse

"""

SWITCH = r"""%% ===== РЕЖИМ ЭКСПОРТА: активна РОВНО ОДНА строка (её меняет драйвер) =====
\AEonly{5}{stat-20m}
%%\AEchrome{hud-frame}
%%\AEchrome{footline-frame}
%%\AEchrome{onair}

"""
# --- frame table: (begin_line, hud_line, end_line, slide_no) --------------
FRAMES = [
    (166, 167, 182, 1),
    (186, 187, 214, 2),
    (218, 219, 241, 3),
    (245, 246, 260, 4),
    (264, 265, 290, 5),
    (294, 295, 320, 6),
    (324, 325, 352, 7),
    (356, 357, 372, 8),
]
for b, h, e, n in FRAMES:
    assert L(b).startswith("\\begin{frame}"), (n, L(b))
    assert L(h) == "  \\hud{%02d}" % n, (n, L(h))
    assert L(e) == "\\end{frame}", (n, L(e))

# --- layer wraps ----------------------------------------------------------
# multi-line spans: emit first line prefixed, middle verbatim, last line + '}'
# single-line: wrap whole line content
# node lines: keep DIRECT \node (tikz breaks when wrapped), append \AEopta/b/c
# to options: empty = visible layer, ",opacity=0" = hidden but geometry kept.


def wrap_span(first, last, macro):  # 1-based inclusive
    return {
        "type": "span",
        "first": first,
        "last": last,
        "prefix": "\\AElayer{%d}{%s}{" % (SLIDE_OF[first], macro),
    }


# slide context per line range (for prefixes)
SLIDE_OF = {}
for b, h, e, n in FRAMES:
    for i in range(b, e + 1):
        SLIDE_OF[i] = n

WRAPS = [
    # slide 3
    {"t": "span", "first": 223, "last": 229, "p": "\\AElayer{3}{panel}{"},
    {"t": "span", "first": 233, "last": 237, "p": "\\AElayer{3}{stat-39456}{"},
    {"t": "line", "line": 240, "p": "\\AElayer{3}{illusnote}{", "s": "}"},
    # slide 5 (stat row: direct nodes + fill/text/draw opacity value macros)
    {
        "t": "node",
        "line": 269,
        "opt": ",fill opacity=\\AEaf,text opacity=\\AEat,draw opacity=\\AEad",
    },
    {
        "t": "node",
        "line": 270,
        "opt": ",fill opacity=\\AEbf,text opacity=\\AEbt,draw opacity=\\AEbd",
    },
    {
        "t": "node",
        "line": 271,
        "opt": ",fill opacity=\\AEcf,text opacity=\\AEct,draw opacity=\\AEcd",
    },
    {"t": "line", "line": 274, "p": "\\AElayer{5}{caption}{", "s": "}"},
    {"t": "span", "first": 277, "last": 286, "p": "\\AElayer{5}{gradient}{"},
    {"t": "line", "line": 289, "p": "\\AElayer{5}{pvalue}{", "s": "}"},
    # Position fix (2026-11-08): a \vphantom of the caption/gradient/pvalue after
    # the stat-row tikzpicture merges into its paragraph line, deepening it so beamer
    # places the whole line ~21px lower than in slides_ru.pdf (proven: z1=312 vs
    # z5=291 bisect, m1=291). The source deck relies on those blocks being REAL
    # text/graphics that naturally break to their own lines; \AElayer{...}{vphantom}
    # is zero-width and would otherwise stay on line 1. Insert an explicit blank
    # line (\par) after \vspace{0.45cm} (before caption) so the phantom starts a
    # fresh paragraph -> identical vertical rhythm to slides_ru.pdf.
]

NODE_RE = re.compile(r"^(\s*)\\node\[(.+?)\]\s*(\(\w+\))\s*\{(.*)\};\s*$")

# --- assemble -------------------------------------------------------------
out = []
i = 1
wrap_by_first = {w["first"]: w for w in WRAPS if w["t"] == "span"}
wrap_by_line = {w["line"]: w for w in WRAPS if w["t"] in ("line", "node")}
ins_after = {}  # line -> [text,...]
ins_before = {}  # line -> [text,...]
for b, h, e, n in FRAMES:
    ins_after.setdefault(b, []).append("\\def\\AEcur{%d}" % n)
    ins_after.setdefault(h, []).append("\\AEbody{%")
    ins_before.setdefault(e, []).append("}%")
# position fix: explicit blank line before caption (line 274) so its \vphantom
# breaks to a fresh paragraph like the real text in slides_ru.pdf (m1=291 test).
ins_before.setdefault(274, []).append("")

while i <= 374:
    if i in wrap_by_first:
        w = wrap_by_first[i]
        out.append(w["p"] + L(w["first"]))
        for j in range(w["first"] + 1, w["last"]):
            out.append(L(j))
        out.append(L(w["last"]) + "}")
        i = w["last"] + 1
        continue
    if i in wrap_by_line:
        for t in ins_before.get(i, []):
            out.append(t)
        w = wrap_by_line[i]
        raw = L(w["line"])
        if w["t"] == "line":
            out.append(w["p"] + raw + w["s"])
        else:
            m = NODE_RE.match(raw)
            assert m, raw
            ind, opts, name, body = m.groups()
            out.append("{}\\node[{}{}]{}{{{}}};".format(ind, opts, w["opt"], name, body))
        i += 1
        continue
    # preamble replacements
    if i == 59:
        out.extend(FOOTLINE.split("\n"))
        i = 65
        continue
    if i == 75:
        out.extend(HUD.split("\n"))
        i = 102
        continue
    if i == 105:
        out.extend(SLIDETITLE.split("\n"))
        i = 117
        continue
    if i == 138:
        out.extend(SETBG.split("\n"))
        i = 151
        continue
    if i == 162:
        out.extend(MACROS.split("\n"))
        out.append(L(162))  # \begin{document}
        out.extend(SWITCH.split("\n"))
        i = 163
        continue
    for t in ins_before.get(i, []):
        out.append(t)
    out.append(L(i))
    for t in ins_after.get(i, []):
        out.append(t)
    i += 1

text = "\n".join(out)
# strip artifacts of split('\n') on empty replacement strings
text = re.sub(r"\n{3,}", "\n\n", text)
with open(DST, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

# --- verify ---------------------------------------------------------------
nl = text.split("\n")
print("out lines:", len(nl))
print("brace balance { - } :", text.count("{") - text.count("}"))
print("AEcur defs:", len([x for x in nl if x.startswith("\\def\\AEcur")]))
print(
    "AEbody open:",
    len([x for x in nl if x == "\\AEbody{%"]),
    " close:",
    len([x for x in nl if x == "}%"]),
)
print(
    "AElayer wraps:",
    len(re.findall(r"\\AElayer\{", text)) - 1,  # minus \slidetitle use
    " nodes-with-opt:",
    len(re.findall(r"\\node\[[^\]]*\\AE[a-c][ftd]\b", text)),
)
print("OK" if text.count("{") == text.count("}") else "BRACE MISMATCH")
