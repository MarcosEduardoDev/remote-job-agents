# Agentes de candidaturas remotas

🇧🇷 Português · [🇬🇧 English](README.en.md)

Sistema de agentes de IA que procura vagas **100% remotas**, monta uma candidatura personalizada para cada
uma e a envia por formulário ou e-mail. Um **agente verificador independente** revisa cada candidatura
antes do envio, e um **monitor** acompanha as respostas das empresas. O candidato só revisa os resultados e
faz as entrevistas.

Construído com [Claude Code](https://claude.com/claude-code) e o Orca (orquestração de agentes em worktrees
e navegador embutido).

## Como funciona

```
 busca diária ──► triagem ──► pacote de candidatura ──► VERIFICADOR ──► envio ──► planilha
 (milhares de     (regras)    (currículo + mensagem      (aprova ou      (formulário   (Google
  vagas)                       + respostas)               reprova)        ou e-mail)    Planilhas)
                                                                                            ▲
                                              monitor de respostas (2x por dia) ────────────┘
```

1. **Busca** (`pesquisa/busca_diaria.py`): consulta as plataformas de recrutamento de mais de 100 empresas
   (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee) e agregadores de vagas remotas
   (Himalayas, Remotive, Workable). Remove vagas já aplicadas e ordena por encaixe com o perfil.
2. **Triagem** (`pesquisa/triagem_detalhada.py`): descobre o link real de candidatura e sinaliza requisitos
   que eliminam o candidato (anos de experiência, idioma acima do nível real, diploma, país, entrevista com IA).
3. **Pacote** (`candidaturas/montar_pacotes.py`): gera o currículo no idioma certo, com só o subtítulo
   adaptado à vaga, e reúne mensagem e respostas do formulário num JSON.
4. **Verificação**: o agente verificador confere cada pacote contra as regras e os dados reais do candidato.
   Sem `APROVADO`, nada é enviado.
5. **Envio**: o agente preenche o formulário no navegador embutido do Orca ou envia o e-mail pelo webmail,
   em segundo plano, e confere a confirmação do site.
6. **Registro e monitoramento**: cada envio entra na planilha; o monitor lê a caixa de entrada duas vezes
   por dia e registra respostas reais, ignorando confirmações automáticas.

## v2: quatro agentes, uma fila compartilhada e "filtrar antes de pensar"

A primeira versão lia mais de 10 mil vagas por rodada e deixava os agentes de IA lerem a maioria. Poucas viravam
candidatura, e quase todo o custo ia para vagas que nunca serviriam. A versão 2 mudou o desenho:

```
 fontes ──► filtros em código ──► fila (pesquisa/fila.py) ──► leitor ──► redator ──► VERIFICADOR ──► candidatador
            local, presencial,     um status por vaga          acha o      modelos      última         envia só o
            lista branca, empresa  + trava de arquivo          formulário  aprovados    barreira       aprovado
            já contatada
```

- **Quatro agentes** (`.claude/agents/`): leitor, redator, verificador e candidatador, cada um com modelo e regras próprios.
- **Fila compartilhada** (`pesquisa/fila.py`): cada vaga tem um status, com trava de arquivo para agentes em paralelo.
- **Filtros em código antes de qualquer agente**: local fora da região, vaga presencial, cargo fora da lista branca e
  empresa já contatada nos últimos 90 dias saem por Python puro, sem gastar token.
- **Medir as fontes**: fonte que nunca rendeu vaga útil é desligada (`ativa: false` em `pesquisa/empresas.json`).
  No nosso caso, 131 de 156 quadros de empresas foram desligados.
- **Respeito aos sites**: sem resolver captcha, sem contornar bloqueio, robots.txt e termos de uso respeitados.
  Sites que bloqueiam automação entram pelos alertas que eles mesmos mandam por e-mail (`pesquisa/alertas.py`).
- **Checagem local** (`verificacao/checar_pacote.py`) pega os motivos de reprovação mais comuns antes do verificador.

## Arquitetura: três agentes em worktrees separadas

| Agente | Função |
|---|---|
| Buscador e postulador | Busca, triagem, pacotes, envio e planilha |
| Verificador | Revisa cada pacote; é o ponto final de segurança (`.claude/agents/verificador.md`) |
| Monitor de respostas | Lê o e-mail duas vezes por dia e registra as respostas |

Cada agente roda numa worktree própria, então nenhum interfere no trabalho do outro, e o verificador não
compartilha contexto com quem montou a candidatura.

## Princípios

As regras completas estão em [`INSTRUCOES.md`](INSTRUCOES.md).

- **Regra de verdade**: o sistema nunca inventa experiência, competência, nível de idioma ou certificado.
  Tudo que uma mensagem ou resposta afirma precisa existir nos dados do candidato.
- **Currículo fixo**: um currículo mestre por idioma; por vaga, só o subtítulo muda. Um script confere que
  o PDF gerado é idêntico ao mestre, exceto pelo subtítulo.
- **Encaixe**: aplica quando o perfil cobre cerca de 40% dos requisitos, quando a vaga é de entrada ou
  quando oferece treinamento. Descarta vagas sênior, presenciais ou restritas a outra região.
- **Regras de parada**: não envia quando o formulário proíbe IA, mostra captcha com desafio, pede opinião
  pessoal, exige gravar vídeo/áudio ou pede um dado que o candidato não forneceu.
- **Limites**: no máximo 2 vagas por empresa por rodada e 1 candidatura por empresa a cada 90 dias.
- **Senhas**: contas em plataformas só com autorização; senha única por site, criptografada com a DPAPI
  do Windows e fora do controle de versão.

## Estrutura

```
INSTRUCOES.md                 regras dos agentes (modelo)
.claude/agents/verificador.md definição do agente verificador
curriculos/
  conteudo/{pt,en,fr}.json    texto do currículo (exemplo com candidato fictício)
  gerar_curriculo.py          gera o PDF; --subtitulo adapta à vaga
  mestres/                    currículos mestres de exemplo em PDF
dados/
  dados-formulario.exemplo.json   modelo dos dados do candidato
pesquisa/
  busca_diaria.py             busca consolidada de vagas
  empresas.json               empresas e suas plataformas de recrutamento
  triagem_detalhada.py        link real de candidatura e requisitos que eliminam
  buscar_vagas.py, ler_vaga.py, ler_pagina.py, buscar_emails.py   leitores por plataforma
  ler_formulario.ps1          lista os campos de um formulário no navegador do Orca
  cofre.ps1                   cria e lê senhas criptografadas (DPAPI)
candidaturas/
  montar_pacotes.py           gera currículos e pacotes a partir de um lote
  lote-exemplo.json           exemplo de lote
verificacao/
  verificar_curriculo.py      confere que o currículo só difere do mestre no subtítulo
```

## Como usar

Requisitos: Windows, Python 3.12+, Claude Code e Orca (com o navegador embutido logado no webmail e nas
plataformas usadas).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1. dados do candidato (o arquivo real fica fora do git)
copy dados\dados-formulario.exemplo.json dados\dados-formulario.json
# edite dados\dados-formulario.json e curriculos\conteudo\*.json com os dados reais

# 2. currículos mestres
.\.venv\Scripts\python.exe curriculos\gerar_curriculo.py

# 3. lista de vagas do dia e triagem
.\.venv\Scripts\python.exe pesquisa\busca_diaria.py --max 40
.\.venv\Scripts\python.exe pesquisa\triagem_detalhada.py 60

# 4. pacotes de um lote e conferência de currículo
.\.venv\Scripts\python.exe candidaturas\montar_pacotes.py candidaturas\lote-exemplo.json
.\.venv\Scripts\python.exe verificacao\verificar_curriculo.py "curriculos\saida\CV - Empresa Exemplo - empresa-exemplo-customer-support.pdf" en
```

Os filtros de região e de idioma em `pesquisa/busca_diaria.py` e `pesquisa/filtrar_vagas.py` estão
configurados para um candidato que mora na Europa; ajuste-os à região e aos idiomas de cada candidato.
O envio e a verificação são feitos pelos agentes (Claude Code + Orca), seguindo `INSTRUCOES.md`.

## Resultados do primeiro teste

Num dia de teste com um candidato real:

| | |
|---|---|
| Vagas lidas pela busca consolidada | 7.510 |
| Candidaturas enviadas e confirmadas | 22 |
| Respostas reais recebidas | 5 (testes de idioma, teste de habilidades, entrevista e uma recusa) |
| Candidaturas barradas pelo verificador antes de chegar à empresa | 9 |

Aprendizados:
- O principal limite é a **oferta**: poucas vagas remotas de entrada aceitam candidatos de qualquer país.
- O verificador evita erros reais: opções que não existem no formulário, respostas sem fonte, captchas.
- Algumas plataformas enviam a candidatura no upload do currículo; o pacote precisa ser aprovado antes.
- Agentes em outras worktrees param quando o orquestrador reinicia; é preciso checar a saúde deles a cada rodada.

## Privacidade

Nenhum dado pessoal real está neste repositório: os exemplos usam um candidato fictício. Os dados reais
(`dados/dados-formulario.json`, currículos gerados, candidaturas, planilha e senhas) ficam fora do git
pelo `.gitignore`.

## Próximos passos

- Rodar a busca diária todos os dias, com envios em lotes revisados pelo verificador.
- Teste de saúde dos agentes no início de cada rodada.
- Leitor de formulários reutilizável por plataforma.
