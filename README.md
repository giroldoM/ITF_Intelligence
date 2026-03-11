ITF INTELLIGENCE

ITF Intelligence is a data science and machine learning platform designed to provide advanced competitive intelligence, scouting, and player development tracking for Junior Tennis.

PROPOSTA DE VALOR (BUSINESS CORE)
---------------------------------
O tenis de base baseia-se muitas vezes em rankings distorcidos pela frequencia de viagens e analises subjetivas. Este projeto resolve isso atraves de matematica rigorosa, extraindo o historico completo da ITF (International Tennis Federation) para calcular a "Forca Verdadeira" de cada atleta.

Em vez de focar apenas em previsoes de apostas, a plataforma gera Scouting Reports para academias, respondendo a perguntas como:
- Qual e o verdadeiro percentil deste atleta face aos jovens da mesma idade exata?
- O jogador e um especialista no Saibro ou um jogador versatil?
- Qual e a curva de momentum (evolucao ou estagnacao) nos ultimos 6 meses?


A ARQUITETURA (PIPELINE)
------------------------
O pipeline e executado em 5 fases distintas, separadas de forma independente para as chaves Masculina e Feminina:

1. Scraping em Duas Ondas: Extracao antibloqueio (curl_cffi) do Top 4000 e dos seus oponentes obscuros ("Fantasmas de Grau 1").
2. Mega-Fusao e Limpeza: Desduplicacao de centenas de milhares de partidas num grafo perfeito de confrontos.
3. Motor de Elo Dinamico (Core): Uma engine cronologica que processa cada jogo, atribuindo o Elo Global e o Elo por Superficie (Bayesian Shrinkage), aplicando K-factors dinamicos baseados na volatilidade do jovem atleta.
4. Feature Engineering: Ajuste de Burn-in e criacao de matrizes de diferencas (elo_diff, surface_elo_diff, age_diff).
5. Machine Learning: Treino de um modelo XGBoost validado com uma estrategia de Out-of-Time Holdout para prever probabilidades reais de vitoria.


ESTRUTURA DO PROJETO
--------------------
itf_intelligence/
 |-- masculino/       (Pipeline completo para a chave masculina)
 |-- feminino/        (Pipeline completo para a chave feminina)
 |-- reporting/       (Em desenvolvimento - Geracao de Scouting Reports em PDF)


COMO EXECUTAR
-------------
1. Instale as dependencias: pip install -r requirements.txt
2. Navegue para a pasta da chave desejada (masculino/ ou feminino/).
3. Execute os scripts na ordem numerica logica (Scrapers -> Cleaner -> Elo -> ML).



VISOES DE RELATORIO (MVP - EM DESENVOLVIMENTO)
----------------------------------------------
O produto final entrega valor atraves de duas oticas complementares, desenhadas especificamente para atender as dores de treinadores, scouts e diretores de academias:

1. RELATORIO INDIVIDUAL (SCOUTING REPORT)
Foco: Raio-X profundo de um unico atleta.
Casos de uso: Avaliacao de desempenho, preparacao de torneios, recrutamento universitario (College Tennis) e justificativa de patrocinio.
Metricas principais:
- Rating Global (Elo absoluto).
- Percentil Ajustado a Idade (ex: "Top 2% entre nascidos em 2008").
- Curva de Momentum (grafico de evolucao ou estagnacao nos ultimos 12 meses).
- Perfil de Superficie (calculo matematico que define se e Especialista ou Versatil).
- Resumo textual gerado automaticamente com os principais insights do atleta.

2. RELATORIO MACRO (ACADEMY BENCHMARK)
Foco: Gestao do portfolio de atletas de um centro de treinamento, rede ou federacao.
Casos de uso: Alocacao de recursos, avaliacao da metodologia de treino e auditoria interna.
Metricas principais:
- Ranking Interno de Promessas (ordenado pelo Elo Ajustado a Idade, revelando quem sao as verdadeiras joias escondidas).
- Rising Stars (os atletas da rede que mais ganharam Elo nos ultimos 3 a 6 meses).
- Diagnostico de Superficie da Academia (ex: identificar se a academia so forma especialistas no Saibro, expondo fraquezas no piso rapido).
- Alertas de Estagnacao (identificacao precoce de atletas que pararam de evoluir matematicamente).
