# Instruções do agente de candidaturas

Regras que os agentes seguem. As decisões específicas de cada candidato (região, idiomas, valores) ficam em
`dados/dados-formulario.json` e na seção "Decisões do candidato" abaixo; elas valem mais que as regras gerais.

## Objetivo
Candidaturas a vagas 100% remotas, de forma automática. O candidato só revisa os resultados e faz as entrevistas.

## Fluxo obrigatório de cada candidatura
1. Achar a vaga e o canal (formulário ou e-mail).
2. Gerar o currículo no idioma da mensagem, só com o subtítulo adaptado.
3. Escrever a mensagem e levantar as respostas do formulário.
4. Montar o pacote `candidaturas/pendentes/<empresa>-<vaga>.json` (campos: empresa, vaga, link_vaga,
   canal, destino, fonte_do_destino, idioma, subtitulo, curriculo, mensagem, respostas, motivo,
   historico_empresa).
5. **Enviar o pacote ao agente `verificador`** (`.claude/agents/verificador.md`). Sem `APROVADO`, nada é
   enviado. Se `REPROVADO`, corrigir e verificar de novo, ou pular a vaga.
6. Enviar exatamente o que foi aprovado, conferir a confirmação do site e atualizar a planilha.
   Em plataforma nova, aprovar o pacote **antes** de anexar o currículo ou avançar etapas: algumas
   plataformas enviam a candidatura no upload do currículo.
7. Mover o pacote para `candidaturas/enviadas/` (ou `reprovadas/`).

## Canais (só dois)
1. **Formulário** da empresa (vaga, candidatura geral ou comunidade de talentos). Se houver campo para se
   apresentar, preencher com a mensagem de apresentação.
2. **E-mail** público de recrutamento escrito no site da empresa. Nunca inventar endereço. Sempre mensagem +
   currículo anexado. Enviar pelo webmail no navegador do Orca e conferir em Itens Enviados.

## Mensagem de apresentação
Breve, de acordo com a vaga, prática, formal, simples e objetiva. Primeira frase: a empresa e a vaga.
Idioma: inglês por padrão; o idioma da empresa quando o candidato o domina. Só fatos do currículo.

## Currículo
- `curriculos/gerar_curriculo.py --idioma <pt|en|fr> --subtitulo "<subtítulo da vaga>"`.
- Idioma do currículo = idioma da mensagem. Só o subtítulo muda por vaga; o resto nunca.

## Escolha da vaga
Aplicar se QUALQUER um valer: o perfil bate ~40% com os requisitos; a vaga é de entrada; a empresa oferece
treinamento. Descartar quando:
- não é 100% remota;
- é restrita a quem mora em outro país ou região;
- é claramente sênior ou de chefia;
- é estágio/trainee que exige faculdade em andamento;
- exige idioma acima do nível real do candidato.
No máximo 2 vagas por empresa por rodada; 1 candidatura por empresa a cada 90 dias.

## Regra de verdade e regras de parada
- Só afirmar o que está nas fontes. Nunca inventar experiência, competência, nível de idioma ou certificado.
- Não enviar (registrar como pulada, com o motivo) quando:
  - o formulário proíbe IA ou exige "minhas próprias palavras";
  - exige declarar idioma ou experiência acima do real;
  - aparece captcha com desafio visível (o agente não resolve captchas);
  - pede opinião pessoal ou dado que não está nas fontes;
  - exige gravar vídeo ou áudio.
- Se a empresa responder pedindo algo novo, avisar o candidato e esperar a decisão dele.

## Contas em plataformas
Só com autorização do candidato. Senha forte e única por site, guardada criptografada com
`pesquisa/cofre.ps1` em `dados/cofre/` (fora do git). Confirmação por e-mail lida no webmail.

## E-mail e monitoramento de respostas
- Webmail aberto no navegador do Orca, na conta dedicada às candidaturas.
- Monitor duas vezes por dia: ignorar confirmações automáticas; qualquer resposta real vira status
  "Respondeu" na planilha, com data, resumo e próximo passo. Nunca responder sem a decisão do candidato.

## Planilha de controle
Google Planilhas com as abas Painel, Candidaturas e Questionário. Status: A pesquisar, Para revisar,
Aprovada, Enviada, Candidato postula, Pulada, Respondeu. O ID da planilha fica só na cópia local do projeto.

## Decisões do candidato
Registre aqui as decisões que mudam as regras acima (região aceita, idiomas e níveis, valor mínimo por hora,
disponibilidade, se aceita freelance), sempre com data.
