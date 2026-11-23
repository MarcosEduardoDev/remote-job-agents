"""Categoria de uma vaga, para medir qual nicho responde mais.

categorizar(titulo, descricao="", tipo_empresa=None) -> "atendimento" | "suporte_tecnico" | "games" | "dev" | "dados_ia" | "outro"

Ordem de decisão: games > suporte_tecnico > atendimento > dev > outro.
- games: player/game support, comunidade ou moderação de jogo, ou empresa marcada como "games" em empresas.json.
- suporte_tecnico: technical support, support engineer, IT support, helpdesk, application support, implementation.
- atendimento: customer support/service/care/success/experience, client advisor, conseiller client,
  chargé de clientèle, téléconseiller, agent.
- dev: developer, backend, software engineer que não seja de suporte.
"""

import re

ORDEM = ["atendimento", "games", "suporte_tecnico", "vendas_recrutamento", "remoto_variado", "dev", "dados_ia", "outro"]
# Lista branca (decisão de 2026-11-22): só estas categorias vão para o redator; "outro" vai para um relatório à parte.
LISTA_BRANCA = {"atendimento", "games", "suporte_tecnico", "vendas_recrutamento", "remoto_variado", "dados_ia", "dev"}
# Decisão de 2026-11-22: funções variadas remotas na Europa (jogos, moderação, eventos, entretenimento, viagens,
# assistência, tradução, testes). Senioridade continua barrada pelo filtro de título.
REMOTO_VARIADO = re.compile(
    r"moderat|community (manager|specialist|coordinator|support)|content review|trust (and|&) safety|"
    r"event(s)? (coordinator|assistant|planner|organi[sz]er|producer)|[ée]v[ée]nementiel|entertainment|animat(eur|rice|ion)|"
    r"circus|cirque|show|travel (agent|advisor|consultant|coordinator)|booking (agent|coordinator)|reservations?|"
    r"virtual assistant|admin(istrative)? assistant|executive assistant|personal assistant|assistant(e)? (administratif|virtuel)|"
    r"data entry|saisie|translat|traduct|locali[sz]ation|interpret|proofread|transcri|subtitl|"
    r"tester|testeur|play ?test|qa analyst|quality assurance|game master|operations (assistant|coordinator)|"
    r"social media (assistant|coordinator|manager)|community|tutor|language (teacher|coach)|chat (agent|operator)", re.I)
JUNIOR = re.compile(r"\bjunior\b|\bjr\.?\b|entry|associate|graduate|d[ée]butant|\bintern\b", re.I)
# Contabilidade e afins não são atendimento, mesmo com "support" no título (ex.: Pennylane "Spécialiste Support Comptable").
CONTABIL = re.compile(r"comptab|accountant|accounting|bookkeep|expert-comptable|paie|payroll|fiscal|audit", re.I)
VENDAS_RECRUTAMENTO = re.compile(
    r"\bsdr\b|\bbdr\b|sales development|business development rep|inside sales|inbound sales|outbound sales|"
    r"t[ée]l[ée]prospect|t[ée]l[ée]vente|t[ée]l[ée]vendeu|commercial s[ée]dentaire|charg[ée]e? de recrutement|"
    r"consultant(e)? en recrutement|recruit(ing|ment)? (consultant|coordinator|assistant|specialist)|"
    r"talent acquisition (coordinator|assistant|specialist)|account executive", re.I)


def na_lista_branca(categoria, titulo):
    """True se a vaga pode ir para o redator. Dev e Account Executive só se forem júnior/entrada."""
    if categoria not in LISTA_BRANCA:
        return False
    if categoria == "dev" and not JUNIOR.search(titulo or ""):
        return False
    if categoria == "vendas_recrutamento" and re.search(r"account executive", titulo or "", re.I) \
            and not JUNIOR.search(titulo or ""):
        return False
    return True  # prioridade na busca

GAMES = re.compile(r"player (support|experience|care)|game(s|r)? (support|master|community|moderat|tester)|"
                   r"gaming (support|customer)|community (manager|moderat|specialist).{0,30}game|"
                   r"(video ?game|jeux? vid[ée]o)|in-game|esports?", re.I)
SUPORTE_TECNICO = re.compile(r"technical support|tech support|support engineer|it support|help ?desk|service desk|"
                             r"application support|implementation|technical customer|support technique|"
                             r"technicien(ne)? support|support informatique|technicien(ne)? informatique|desktop support|it operations|it engineer|"
                             r"it service|service dispatcher|systems adoption|\bL[1-3] support|engineer[^,]{0,25}\bsupport\b|support (N1|N2|N3|niveau)", re.I)
ATENDIMENTO = re.compile(r"customer (support|service|care|success|experience|advocate|advisor)|client "
                         r"(advisor|support|service|care|success)|conseill[eè]re? client|charg[ée]e? de client[eè]le|"
                         r"t[ée]l[ée]conseill|service client|support client|relation client|\bagent\b|"
                         r"\bcx\b|help center|contact center|call center|support specialist|sp[ée]cialiste support|employee support|"
                         r"account services|care ops|customer operations|billing support|platform support", re.I)
DADOS_IA = re.compile(r"\brater\b|annotat|label(l)?ing|ai trainer|ai tutor|llm|\brlhf\b|prompt (and|&) response|prompt engineer(ing)? evaluat|"
                      r"search (quality|engine) (evaluator|rater)|ads? (quality )?evaluat|evaluations? specialist|transcri(ption|ber)|"
                      r"linguist|audio (specialist|evaluat)|voice (actor|recording|contributor)|data (contributor|specialist)|"
                      r"subject matter expert|\bSME\b|ai data|trainai|generative audio", re.I)
DEV_FORTE = re.compile(r"developer|d[ée]veloppeu|software engineer|programmer|backend|back-end|full[- ]?stack", re.I)
DEV = re.compile(r"developer|d[ée]veloppeu|backend|back-end|software engineer|full[- ]?stack|programmer|data engineer|"
                 r"analytics engineer|platform engineer|infrastructure engineer|site reliability|machine learning engineer|"
                 r"\bjava\b|spring", re.I)


def categorizar(titulo: str, descricao: str = "", tipo_empresa: str | None = None) -> str:
    titulo = titulo or ""
    descricao = (descricao or "")[:4000]
    if CONTABIL.search(titulo):
        return "outro"
    if tipo_empresa == "games" or GAMES.search(titulo) or GAMES.search(descricao[:600]):
        return "games"
    if DADOS_IA.search(titulo):
        return "dados_ia"
    if SUPORTE_TECNICO.search(titulo):
        return "suporte_tecnico"
    if DEV_FORTE.search(titulo):  # "Developer ... Agent" é dev, não atendimento
        return "dev"
    if VENDAS_RECRUTAMENTO.search(titulo):
        return "vendas_recrutamento"
    if REMOTO_VARIADO.search(titulo):
        return "remoto_variado"
    if ATENDIMENTO.search(titulo):
        return "atendimento"
    if DEV.search(titulo):
        return "dev"
    # Título vago: usa a descrição como desempate.
    if SUPORTE_TECNICO.search(descricao):
        return "suporte_tecnico"
    if ATENDIMENTO.search(descricao):
        return "atendimento"
    return "outro"


if __name__ == "__main__":
    testes = [
        ("Player Support Agent - French", "", None, "games"),
        ("Customer Support Specialist", "", None, "atendimento"),
        ("Conseiller client en télétravail", "", None, "atendimento"),
        ("Chargé de clientèle bilingue portugais", "", None, "atendimento"),
        ("Technical Support Engineer", "", None, "suporte_tecnico"),
        ("Junior Backend Developer (Java)", "", None, "dev"),
        ("Software Engineer - L3 Support", "", None, "suporte_tecnico"),
        ("Customer Service Representative", "", "games", "games"),
        ("Recruiting Coordinator", "", None, "outro"),
        ("Technicien(ne) Support Informatique - 100% TELETRAVAIL", "", None, "suporte_tecnico"),
        ("Développeur Open Policy Agent (OPA) / Rego - Full remote", "", None, "dev"),
        ("Customer Service Agent", "", None, "atendimento"),
        ("AI Data Specialist - French", "", None, "dados_ia"),
        ("Search Engine Evaluator - French (France)", "", None, "dados_ia"),
        ("Portuguese Audio Evaluations Specialist - Freelance AI Trainer Project", "", None, "dados_ia"),
        ("Prompt & Response Evaluator", "", None, "dados_ia"),
        ("Video Annotation – Remote (Worldwide)", "", None, "dados_ia"),
        ("Spécialiste Support Pilotage et Comptabilité", "", None, "atendimento"),
        ("IT Service Dispatcher / Coordinator - Remote", "", None, "suporte_tecnico"),
        ("Platform Support Specialist", "", None, "atendimento"),
        ("Account Executive SMB", "", None, "outro"),
        ("Data Engineer", "", None, "dev"),
        ("Operations Associate", "You will answer customer service tickets.", None, "atendimento"),
    ]
    falhas = 0
    for titulo, desc, tipo, esperado in testes:
        obtido = categorizar(titulo, desc, tipo)
        ok = obtido == esperado
        falhas += not ok
        print(f"{'OK ' if ok else 'ERRO'} {titulo!r} -> {obtido} (esperado {esperado})")
    print(f"{len(testes) - falhas}/{len(testes)} corretos")
