% Minimal replacement for agujournal2019.cls
% Wraps article class with AGU-compatible commands.
% For final submission to Space Weather, use the official AGU class
% from https://www.agu.org/publish-with-agu/publish

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{agujournal2019}[2026/10/08 minimal stub for arXiv preprint]

\DeclareOption{draft}{\PassOptionsToClass{draft}{article}}
\DeclareOption{final}{\PassOptionsToClass{final}{article}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass[12pt,a4paper]{article}

\RequirePackage{geometry}
\geometry{margin=1in}

\RequirePackage{setspace}
\onehalfspacing

\RequirePackage{etoolbox}

\newcommand{\journalname}[1]{\newcommand{\@journalname}{#1}}

% AGU-style authors/affiliations
% \authors{Alexey Petrov\affil{1}, Makar Petrov\affil{1}}
% \affiliation{1}{Independent researchers, City, Country}
\def\@authors{}
\def\@affiliations{}
\def\@corrauthor{}
\def\@corremail{}

\newcommand{\affil}[1]{\textsuperscript{#1}}

\newcommand{\authors}[1]{%
  \def\@authors{#1}%
}

\newcommand{\affiliation}[2]{%
  \appto{\@affiliations}{%
    \par\noindent\textsuperscript{#1}#2%
  }%
}

\newcommand{\correspondingauthor}[2]{%
  \appto{\@authors}{\thanks{Corresponding author: #2}}%
  \def\@corrauthor{#1}%
  \def\@corremail{#2}%
}

% Override \maketitle to use AGU-style layout
\renewcommand{\maketitle}{%
  \begin{flushleft}
  {\LARGE\bfseries\@title\par}
  \vskip 1.5em
  {\large\@authors\par}
  \vskip 0.5em
  {\small\@affiliations\par}
  \vskip 1em
  {\small\@date\par}
  \end{flushleft}
  \vskip 1.5em
}

% keypoints environment
\newenvironment{keypoints}{%
  \subsection*{Key Points}
  \begin{itemize}
}{%
  \end{itemize}
}

% AGU-style section numbering
\renewcommand\thesection{\arabic{section}}
\renewcommand\thesubsection{\thesection.\arabic{subsection}}
\renewcommand\thesubsubsection{\thesubsection.\arabic{subsubsection}}

% AGU-style abstract
\renewenvironment{abstract}{%
  \begin{center}
  {\bfseries\large Abstract}
  \end{center}
  \vspace{-0.5em}
  \small
}{%
  \normalsize
}

% AGU-style section headings
\RequirePackage{titlesec}
\titleformat{\section}
  {\normalfont\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}
  {\normalfont\large\bfseries}{\thesubsection}{1em}{}
\titleformat{\subsubsection}
  {\normalfont\normalsize\bfseries}{\thesubsubsection}{1em}{}

% Figure/table captions AGU-style
\RequirePackage{caption}
\captionsetup[figure]{font=small,labelfont=bf,labelsep=period}
\captionsetup[table]{font=small,labelfont=bf,labelsep=period}