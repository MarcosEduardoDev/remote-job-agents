# Remote job application agents

[🇧🇷 Português](README.md) · 🇬🇧 English

A system of AI agents that finds **fully remote** jobs, builds a tailored application for each one and
submits it through the company's form or by e-mail. An **independent verifier agent** reviews every
application before it is sent, and a **monitor** tracks company replies. The candidate only reviews the
results and attends interviews.

Built with [Claude Code](https://claude.com/claude-code) and Orca (agent orchestration across worktrees
with an embedded browser).

## How it works

```
 daily search ──► screening ──► application package ──► VERIFIER ──► submission ──► spreadsheet
 (thousands       (rules)       (CV + message           (approve or    (form or       (Google
  of jobs)                       + form answers)          reject)        e-mail)        Sheets)
                                                                                           ▲
                                               reply monitor (twice a day) ────────────────┘
```

1. **Search** (`pesquisa/busca_diaria.py`): queries the applicant tracking systems of more than 100
   companies (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee) and remote job boards
   (Himalayas, Remotive, Workable). Removes jobs already applied to and ranks the rest by profile fit.
2. **Screening** (`pesquisa/triagem_detalhada.py`): finds the real application link and flags requirements
   that rule the candidate out (years of experience, language above the real level, degree, country, AI interview).
3. **Package** (`candidaturas/montar_pacotes.py`): generates the CV in the right language, with only the
   subtitle tailored to the job, and gathers the message and form answers in a JSON file.
4. **Verification**: the verifier agent checks each package against the rules and the candidate's real
   data. Nothing is sent without `APROVADO` (approved).
5. **Submission**: the agent fills in the form in Orca's embedded browser or sends the e-mail through
   webmail, in the background, and checks the site's confirmation.
6. **Tracking and monitoring**: every submission goes into the spreadsheet; the monitor reads the inbox
   twice a day and records real replies, ignoring automatic confirmations.

## v2: four agents, a shared queue and "filter before you think"

The first version scanned 10,000+ job posts per run and let AI agents read most of them. Very few turned into
applications, and most of the cost went into reading posts that could never fit. Version 2 changed the shape:

```
 sources ──► code filters ──► queue (pesquisa/fila.py) ──► reader ──► writer ──► VERIFIER ──► applicant
             location, on-site,   one status per job       finds the   approved    final gate   submits only
             whitelist, company   + file lock              real form   templates                approved ones
             already contacted
```

- **Four agents** (`.claude/agents/`): reader, writer, verifier and applicant, each with its own model and rules.
- **Shared queue** (`pesquisa/fila.py`): every job has one status (triaged, read in browser, package, approved,
  sent, manual...), with a file lock so agents running in parallel never overwrite each other.
- **Code filters before any agent**: location outside the target region, on-site roles, job titles outside the
  whitelist and companies already contacted in the last 90 days are dropped by plain Python, at zero token cost.
- **Measure the sources**: sources that never produced a useful job are switched off (`ativa: false` in
  `pesquisa/empresas.json`). In our case 131 of 156 company boards were turned off.
- **Respect the sites**: no captcha solving, no bypassing bot protection, robots.txt and terms of use respected.
  Sites that block automation are reached through the job alerts they send by e-mail (`pesquisa/alertas.py`).
- **Local pre-check** (`verificacao/checar_pacote.py`) catches the most common rejection reasons before the
  verifier runs.

## Architecture: three agents in separate worktrees

| Agent | Role |
|---|---|
| Searcher and applicant | Search, screening, packages, submission and spreadsheet |
| Verifier | Reviews every package; the final safety gate (`.claude/agents/verificador.md`) |
| Reply monitor | Reads the inbox twice a day and records replies |

Each agent runs in its own worktree, so none interferes with the others, and the verifier does not share
context with the agent that built the application.

## Principles

The full rules are in [`INSTRUCOES.md`](INSTRUCOES.md) (in Portuguese).

- **Truth rule**: the system never invents experience, skills, language levels or certificates. Everything
  a message or answer states must exist in the candidate's data.
- **Fixed CV**: one master CV per language; only the subtitle changes per job. A script checks that the
  generated PDF is identical to the master except for the subtitle.
- **Fit**: applies when the profile covers about 40% of the requirements, when the job is entry-level or
  when it offers training. Skips senior, on-site or region-restricted jobs.
- **Stop rules**: does not submit when the form forbids AI, shows a captcha challenge, asks for a personal
  opinion, requires recording video/audio or asks for data the candidate has not provided.
- **Limits**: at most 2 jobs per company per round and 1 application per company every 90 days.
- **Passwords**: platform accounts only with authorization; one unique password per site, encrypted with
  Windows DPAPI and kept out of version control.

## Structure

```
INSTRUCOES.md                 agent rules (template)
.claude/agents/verificador.md verifier agent definition
curriculos/
  conteudo/{pt,en,fr}.json    CV text (example with a fictional candidate)
  gerar_curriculo.py          generates the PDF; --subtitulo tailors it to the job
  mestres/                    example master CVs as PDF
dados/
  dados-formulario.exemplo.json   template for the candidate's data
pesquisa/
  busca_diaria.py             consolidated job search
  empresas.json               companies and their recruiting platforms
  triagem_detalhada.py        real application link and disqualifying requirements
  buscar_vagas.py, ler_vaga.py, ler_pagina.py, buscar_emails.py   per-platform readers
  ler_formulario.ps1          lists the fields of a form in Orca's browser
  cofre.ps1                   creates and reads encrypted passwords (DPAPI)
candidaturas/
  montar_pacotes.py           builds CVs and packages from a batch file
  lote-exemplo.json           example batch
verificacao/
  verificar_curriculo.py      checks that a CV differs from the master only in the subtitle
```

## Usage

Requirements: Windows, Python 3.12+, Claude Code and Orca (with its embedded browser signed in to webmail
and the platforms in use).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1. candidate data (the real file stays out of git)
copy dados\dados-formulario.exemplo.json dados\dados-formulario.json
# edit dados\dados-formulario.json and curriculos\conteudo\*.json with the real data

# 2. master CVs
.\.venv\Scripts\python.exe curriculos\gerar_curriculo.py

# 3. today's job list and screening
.\.venv\Scripts\python.exe pesquisa\busca_diaria.py --max 40
.\.venv\Scripts\python.exe pesquisa\triagem_detalhada.py 60

# 4. packages for a batch and CV check
.\.venv\Scripts\python.exe candidaturas\montar_pacotes.py candidaturas\lote-exemplo.json
.\.venv\Scripts\python.exe verificacao\verificar_curriculo.py "curriculos\saida\CV - Empresa Exemplo - empresa-exemplo-customer-support.pdf" en
```

The region and language filters in `pesquisa/busca_diaria.py` and `pesquisa/filtrar_vagas.py` are set up
for a candidate living in Europe; adjust them to each candidate's region and languages.
Submission and verification are done by the agents (Claude Code + Orca), following `INSTRUCOES.md`.

## First test results

In one test day with a real candidate:

| | |
|---|---|
| Jobs read by the consolidated search | 7,510 |
| Applications sent and confirmed | 22 |
| Real replies received | 5 (language tests, a skills test, an interview and one rejection) |
| Applications stopped by the verifier before reaching a company | 9 |

Lessons learned:
- The main limit is **supply**: few remote entry-level jobs accept candidates from any country.
- The verifier prevents real mistakes: options that do not exist in the form, answers with no source, captchas.
- Some platforms submit the application as soon as the CV is uploaded; the package must be approved first.
- Agents in other worktrees stop when the orchestrator restarts; their health must be checked every round.

## Privacy

No real personal data is in this repository: the examples use a fictional candidate. Real data
(`dados/dados-formulario.json`, generated CVs, applications, spreadsheet and passwords) is kept out of git
by `.gitignore`.

## Next steps

- Run the daily search every day, submitting in batches reviewed by the verifier.
- Agent health check at the start of each round.
- Reusable per-platform form reader.
