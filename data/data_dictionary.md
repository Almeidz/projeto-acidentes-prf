# Dicionário de dados — `data/processed/acidentes_prf_tratado.csv.gz`

**Fonte primária:** Polícia Rodoviária Federal (PRF), dados abertos de acidentes
(<https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf>), obtidos pela versão agrupada por ocorrência do Kaggle
(<https://www.kaggle.com/datasets/equeiroz/acidentes-rodovias-federais-brasil-jan07-a-jul19>).
**Granularidade:** 1 linha = 1 acidente (ocorrência). **Cobertura:** 2007–2018 e 2020 (o arquivo de 2019 não está na base usada).
**Formato:** CSV separado por vírgula, UTF-8, compactado (gzip). Ausentes = campo vazio. Datas em `AAAA-MM-DD`.

> **Chave:** `(ano, id)`. O `id` repete-se em anos diferentes (acidentes distintos); não use `id` sozinho como chave.

| Variável | Tipo | Formato / valores | Significado |
|---|---|---|---|
| `id` | inteiro | — | Identificador da ocorrência dentro do arquivo anual da PRF. |
| `data` | data | `AAAA-MM-DD` | Data do acidente (originalmente em 3 formatos, unificados). |
| `ano` | inteiro | 2007–2020 | Ano extraído de `data`. |
| `hora` | inteiro | 0–23 | Hora cheia do acidente (extraída de `horario`). |
| `dia_semana` | texto | segunda, terça, quarta, quinta, sexta, sábado, domingo | Dia da semana (grafias unificadas). |
| `uf` | texto | sigla com 2 letras | Unidade da Federação do acidente. Ausente em 12 registros. |
| `br` | decimal | ex.: 116 | Número da rodovia federal (BR-xxx). Ausente em 430 registros. |
| `km` | decimal | 0–5000, ponto decimal | Quilômetro da rodovia. Valores fora de [0, 5000] foram anulados (77 casos). |
| `municipio` | texto | MAIÚSCULAS, sem acento | Município do acidente (como na fonte). |
| `causa_grupo` | texto | 11 grupos (ver abaixo) | Causa **agrupada** por regras em `src/etl.py` (decisão analítica nossa). |
| `causa_norm` | texto | minúsculas, sem acento | Causa original normalizada (64 grafias). Taxonomia da PRF mudou em 2017. |
| `tipo_acidente` | texto | ex.: Colisão frontal | Tipo do acidente (26 valores). |
| `classificacao` | texto | Sem vítimas; Com vítimas feridas; Com vítimas fatais; Ignorado | Classificação da PRF. Pode divergir de `gravidade` em registros antigos. |
| `gravidade` | texto | fatal; com_feridos; sem_vitimas | **Derivada:** fatal se `mortos`>0; com_feridos se `feridos`>0; senão sem_vitimas. |
| `fase_dia` | texto | Pleno dia; Plena noite; Amanhecer; Anoitecer | Fase do dia. |
| `condicao_meteorologica` | texto | Céu claro, Nublado, Chuva, Sol, Nevoeiro/neblina, Garoa/chuvisco, Vento, Granizo, Neve, Ignorada | Condição do tempo (`Ignorada` = não informada). |
| `tipo_pista` | texto | Simples; Dupla; Múltipla | Tipo da pista. |
| `pessoas` | inteiro | ≥ 1 | Total de pessoas envolvidas. |
| `mortos` | inteiro | ≥ 0 | Pessoas mortas no acidente. |
| `feridos_leves` | inteiro | ≥ 0 | Feridos leves. |
| `feridos_graves` | inteiro | ≥ 0 | Feridos graves. |
| `ilesos` | inteiro | ≥ 0 | Pessoas ilesas. |
| `feridos` | inteiro | ≥ 0 | Total de feridos (= `feridos_leves` + `feridos_graves`, verificado em 100% das linhas). |
| `veiculos` | inteiro | ≥ 1 | Veículos envolvidos. |
| `latitude` | decimal | graus, ponto decimal | Só existe a partir de 2017 (≈ 87% ausente na série). |
| `longitude` | decimal | graus, ponto decimal | Idem. |
| `flag_inconsistente` | booleano | True/False | True se `mortos + feridos > pessoas` (nenhum caso observado). |

## Grupos de `causa_grupo`
Falta de atenção · Velocidade incompatível · Distância de segurança · Álcool / substâncias · Sono do condutor ·
Desobediência às normas · Defeito mecânico · Animais na pista · Condições da via / ambiente · Pedestre · Outras / ignorada.

## Colunas da fonte **não** mantidas
`sentido_via`, `tracado_via`, `uso_solo` (mudou de significado em 2017: Urbano/Rural → Sim/Não), `regional`, `delegacia`, `uop`
(existem só a partir de 2017), `ano` original (ausente em 2016; recalculado de `data`).

## Métricas usadas nas análises
* **Letalidade** = mortos ÷ acidentes × 100.
* **% de acidentes fatais** = acidentes com ≥ 1 morte ÷ acidentes × 100.
