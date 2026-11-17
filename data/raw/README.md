# Dados brutos

Os 13 arquivos `datatran2007.csv … datatran2020.csv` (≈ 400 MB, **sem** `datatran2019.csv` na base usada) não são versionados (> 50 MB).

**Como obter**
1. Baixe o dataset no Kaggle: <https://www.kaggle.com/datasets/equeiroz/acidentes-rodovias-federais-brasil-jan07-a-jul19>
   (botão *Download*, arquivo `archive.zip`) **ou** os arquivos originais no portal da PRF:
   <https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf>
2. Descompacte os `datatran*.csv` nesta pasta (`data/raw/`).
3. Rode `python -m src.etl --raw data/raw --out data/processed`.

Opcionalmente, `python -m src.download_data` tenta o download automático via `kagglehub` (não testado pelos autores).

> Não é necessário refazer o ETL para ver as análises: `data/processed/acidentes_prf_tratado.csv.gz` já está no repositório.
