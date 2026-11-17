# Acidentes em rodovias federais brasileiras (2007–2020)

Projeto final da disciplina **Linguagem de Programação (Análise e Visualização de Dados com Python)** — 6º período,
Bacharelado em Sistemas de Informação · *[Unilasalle-RJ]* · *[2°semestre/2026]*

**Autor:** Lucas de Almeida Brugger Cavalcante 

🔗 **Artigo (GitHub Pages):** <https://almeidz.github.io/projeto-acidentes-prf/> · 📓 **Notebook:** [`notebooks/analise_exploratoria.ipynb`](notebooks/analise_exploratoria.ipynb)

![Python](https://img.shields.io/badge/python-3.12-blue) ![Licença código](https://img.shields.io/badge/código-MIT-green) ![Licença dados](https://img.shields.io/badge/dados%20e%20texto-CC--BY%204.0-lightgrey) ![FAIR](https://img.shields.io/badge/FAIR-sim-brightgreen)

## Resumo executivo
Analisamos 1.784.419 ocorrências da Polícia Rodoviária Federal (PRF) entre 2007 e 2020 (sem 2019, ausente da base usada) com um pipeline
determinístico em Python/pandas que unifica 13 arquivos anuais com codificações, formatos de data e taxonomias distintas. Perguntas de pesquisa:

* **RQ1** – evolução de acidentes, mortos e letalidade (e se ela é comparável ao longo do tempo);
* **RQ2** – causas, tipos e condições associados à gravidade;
* **RQ3** – distribuição geográfica das mortes (UF e trechos de 10 km).

Achado metodológico central: a letalidade aparente sobe, mas a parcela de acidentes *sem vítimas* cai de ~60% para ~18%, o que indica mudança no registro
e não apenas na segurança viária. Detalhes, gráficos interativos e limitações no artigo.

**Palavras-chave:** acidentes de trânsito; rodovias federais; Polícia Rodoviária Federal; análise exploratória; dados abertos; FAIR.

## Fonte dos dados
* PRF – Dados abertos: <https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf>
* Versão utilizada (Kaggle): <https://www.kaggle.com/datasets/equeiroz/acidentes-rodovias-federais-brasil-jan07-a-jul19>

## Estrutura
```
projeto-acidentes-prf/
├── README.md · LICENSE (MIT) · LICENSE-CC-BY-4.0.md · requirements.txt · .gitignore
├── data/
│   ├── raw/                      # brutos (não versionados, ver data/raw/README.md)
│   ├── processed/                # acidentes_prf_tratado.csv.gz + etl_log.json
│   └── data_dictionary.md        # dicionário de variáveis (FAIR)
├── notebooks/analise_exploratoria.ipynb
├── src/
│   ├── etl.py                    # limpeza e unificação (com log de descartes)
│   ├── analise.py                # agregações/estatísticas (RQ1–RQ3)
│   ├── figuras.py                # figuras estáticas (matplotlib)
│   ├── build_artigo.py           # gera docs/index.html com os números calculados
│   └── download_data.py          # download opcional (não testado)
└── docs/                         # artigo publicado no GitHub Pages
    ├── index.html
    └── assets/                   # figuras PNG
```

## Como reproduzir
```bash
git clone https://github.com/Almeidz/projeto-acidentes-prf.git
cd projeto-acidentes-prf
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (opcional) refazer o ETL a partir dos brutos em data/raw/
python -m src.etl --raw data/raw --out data/processed

python -m src.build_artigo        # regenera docs/index.html
jupyter notebook notebooks/analise_exploratoria.ipynb   # requer `pip install notebook`
```
O notebook também roda no **Google Colab**: abra-o a partir do GitHub; a primeira célula clona o repositório.

> **Observações:** `requirements.txt` fixa as versões usadas no desenvolvimento (Python 3.12, pandas 3.x). O gráfico interativo do artigo usa
> Plotly.js (CDN, versão fixa), de modo que o Plotly **não** é dependência Python. O `src/etl.py` foi testado com os dados e versões acima.

## Publicar no GitHub Pages
No repositório: **Settings → Pages → Build and deployment → Branch: `main` / pasta `/docs`** → Save. A URL acima passa a servir `docs/index.html`.

## Conformidade FAIR
| Princípio | Como é atendido |
|---|---|
| Findable | README com resumo, palavras-chave e fonte; autoria/disciplina no cabeçalho dos artefatos |
| Accessible | Repositório público; nenhuma credencial necessária para rodar a partir dos dados tratados; artigo responsivo no GitHub Pages |
| Interoperable | Dados tratados em `.csv.gz`; `data/data_dictionary.md` |
| Reusable | MIT (código) e CC-BY 4.0 (dados tratados e texto); `requirements.txt` com versões fixas |

## Licenças
Código: [MIT](LICENSE). Texto, figuras e dados tratados: [CC BY 4.0](LICENSE-CC-BY-4.0.md). Os registros originais pertencem à PRF e seguem os termos do portal de dados abertos.
