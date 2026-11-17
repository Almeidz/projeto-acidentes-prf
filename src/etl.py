"""ETL dos dados de acidentes em rodovias federais (PRF, 2007-2020).

Uso:
    python -m src.etl --raw data/raw --out data/processed

Princípios: determinístico, sem alterar os arquivos brutos e com log de
rastreabilidade (quantas linhas foram lidas/descartadas e por quê).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd

KM_MAX = 5000  # maior rodovia federal (BR-116/BR-101) tem < 5.000 km

NULL_TOKENS = {"", "(null)", "null", "nan", "none"}

NUM_COLS = ["pessoas", "mortos", "feridos_leves", "feridos_graves",
            "ilesos", "ignorados", "feridos", "veiculos"]

DIAS = {"segunda": "segunda", "terca": "terça", "quarta": "quarta",
        "quinta": "quinta", "sexta": "sexta", "sabado": "sábado",
        "domingo": "domingo"}

# Agrupamento das causas (a taxonomia da PRF mudou em 2017).
# A ordem importa: a primeira regra que casar vence.
CAUSA_REGRAS = [
    ("Pedestre", ["pedestre", "entrada inopinada"]),
    ("Álcool / substâncias", ["alcool", "substancias psicoativas"]),
    ("Sono do condutor", ["dormindo"]),
    ("Falta de atenção", ["falta de atencao", "condutor usando celular", "reacao tardia",
                          "ausencia de reacao", "frear bruscamente"]),
    ("Velocidade incompatível", ["velocidade incompativel"]),
    ("Distância de segurança", ["distancia de seguranca", "distancia do veiculo da frente"]),
    ("Desobediência às normas", ["desobediencia", "ultrapassagem indevida", "contramao",
                                 "conversao proibida", "preferencia no cruzamento",
                                 "semaforo", "mudanca de faixa", "entre as faixas",
                                 "transitar no acostamento", "acessar a via",
                                 "acesso irregular", "estacionar ou parar"]),
    ("Defeito mecânico", ["defeito mecanico", "avarias", "falhas mecanicas",
                          "iluminacao/sinalizacao do veiculo", "carga excessiva"]),
    ("Animais na pista", ["animais na pista"]),
    ("Condições da via / ambiente", ["defeito na via", "pista escorregadia", "sinalizacao da via",
                                     "objeto estatico", "falta de acostamento",
                                     "acostamento em desnivel", "pista esburacada",
                                     "iluminacao deficiente", "ausencia de sinalizacao",
                                     "acumulo", "afundamento", "demais falhas na via", "chuva",
                                     "fumaca", "restricao de visibilidade",
                                     "fenomenos da natureza"]),
    ("Outras / ignorada", ["outras", "mal subito", "agressao externa"]),
]


def normalizar_texto(s: pd.Series) -> pd.Series:
    """strip, minúsculas, sem acentos, espaços colapsados; '(null)' -> NA."""
    s = s.astype("string").str.strip()
    s = s.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
    s = s.str.lower().str.replace(r"\s+", " ", regex=True)
    return s.mask(s.isin(NULL_TOKENS))


def agrupar_causa(causa_norm: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=causa_norm.index, dtype="string")
    for grupo, chaves in CAUSA_REGRAS:
        padrao = "|".join(re.escape(c) for c in chaves)
        casou = causa_norm.str.contains(padrao, na=False) & out.isna()
        out[casou] = grupo
    out[out.isna() & causa_norm.notna()] = "Outras / ignorada"
    return out


def parse_data(s: pd.Series) -> pd.Series:
    """Três formatos observados: AAAA-MM-DD, DD/MM/AAAA e DD/MM/AA."""
    s = s.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for regex, fmt in ((r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
                       (r"^\d{2}/\d{2}/\d{4}$", "%d/%m/%Y"),
                       (r"^\d{2}/\d{2}/\d{2}$", "%d/%m/%y")):
        m = s.str.match(regex, na=False)
        if m.any():
            out[m] = pd.to_datetime(s[m], format=fmt)
    return out


def ler_arquivo(caminho: str) -> pd.DataFrame:
    """Lê um CSV anual (separador ';'). Codificação varia: utf-8 (2020) ou latin-1."""
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=";", encoding=enc, dtype=str, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível decodificar {caminho}")


def tratar(df: pd.DataFrame, log: dict, nome: str) -> pd.DataFrame:
    n0 = len(df)
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    df["data"] = parse_data(df["data_inversa"])
    df["ano"] = df["data"].dt.year.astype("Int16")

    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("br", "km"):
        df[c] = pd.to_numeric(df[c].astype("string").str.strip()
                              .str.replace(",", ".", regex=False), errors="coerce")
    # km fora de [0, KM_MAX] é erro de digitação (observado: valores negativos e > 9000)
    km_invalido = df["km"].notna() & ~df["km"].between(0, KM_MAX)
    df.loc[km_invalido, "km"] = np.nan
    for c in ("latitude", "longitude"):
        if c in df:
            df[c] = pd.to_numeric(df[c].astype("string").str.replace(",", ".", regex=False),
                                  errors="coerce")
        else:
            df[c] = np.nan

    hora = pd.to_datetime(df["horario"].astype("string").str.strip(),
                          format="%H:%M:%S", errors="coerce")
    df["hora"] = hora.dt.hour.astype("Int8")

    dia = normalizar_texto(df["dia_semana"]).str.replace("-feira", "", regex=False)
    df["dia_semana"] = dia.map(DIAS).astype("string")

    uf = df["uf"].astype("string").str.strip().str.upper()
    df["uf"] = uf.mask(uf.str.lower().isin(NULL_TOKENS))
    df["municipio"] = df["municipio"].astype("string").str.strip().str.upper()

    df["causa_norm"] = normalizar_texto(df["causa_acidente"])
    df["causa_grupo"] = agrupar_causa(df["causa_norm"])
    # Colunas categóricas: chave normalizada (para unificar variações) + rótulo original
    # (com acento) recuperado depois em `rotular_categorias`.
    fontes = {"tipo_acidente": "tipo_acidente", "classificacao": "classificacao_acidente",
              "fase_dia": "fase_dia", "condicao_meteorologica": "condicao_metereologica",
              "tipo_pista": "tipo_pista"}
    for novo, orig in fontes.items():
        original = df[orig].astype("string").str.strip()
        df[novo] = normalizar_texto(df[orig])
        df[novo + "__orig"] = original.mask(original.str.lower().isin(NULL_TOKENS))
    # 'Ignorada' (2007-2016) e 'Ignorado' (2017+) são o mesmo valor
    df["condicao_meteorologica"] = df["condicao_meteorologica"].replace({"ignorada": "ignorado"})

    # Métrica derivada e sinalização (não remoção) de inconsistências
    df["flag_inconsistente"] = ((df["mortos"] + df["feridos"]) > df["pessoas"]).fillna(False)
    df["gravidade"] = np.select([df["mortos"] > 0, df["feridos"] > 0],
                                ["fatal", "com_feridos"], default="sem_vitimas")

    # Descartes rastreáveis. `id` repetido no MESMO arquivo = mesmo acidente listado duas
    # vezes com clima/tipo de pista divergentes (verificado na auditoria): mantém-se a 1ª linha.
    # O `id` NÃO é único entre arquivos de anos diferentes: a chave é (ano, id).
    sem_data = df["data"].isna()
    dup = df.duplicated(subset=["id"], keep="first")
    log[nome] = {"linhas_lidas": int(n0), "descartadas_sem_data": int(sem_data.sum()),
                 "descartadas_id_duplicado": int(dup.sum()),
                 "uf_ausente": int(df["uf"].isna().sum()),
                 "br_ausente": int(df["br"].isna().sum()),
                 "km_invalido_anulado": int(km_invalido.sum()),
                 "flag_inconsistente": int(df["flag_inconsistente"].sum())}
    df = df[~sem_data & ~dup]

    cols = ["id", "data", "ano", "hora", "dia_semana", "uf", "br", "km", "municipio",
            "causa_grupo", "causa_norm", "tipo_acidente", "classificacao", "gravidade",
            "fase_dia", "condicao_meteorologica", "tipo_pista",
            "pessoas", "mortos", "feridos_leves", "feridos_graves", "ilesos",
            "feridos", "veiculos", "latitude", "longitude", "flag_inconsistente"]
    cols += [c for c in df.columns if c.endswith("__orig")]
    return df[cols]


def rotular_categorias(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada chave normalizada escolhe o rótulo original mais frequente
    (preferindo a grafia com acento) e descarta as colunas auxiliares."""
    for col in [c[:-6] for c in df.columns if c.endswith("__orig")]:
        orig = df[col + "__orig"]
        tem_acento = orig.str.contains(r"[^\x00-\x7f]", na=False)
        tab = (pd.DataFrame({"k": df[col], "o": orig, "a": tem_acento})
               .dropna(subset=["k", "o"]).groupby(["k", "o", "a"]).size().reset_index(name="n")
               .sort_values(["k", "a", "n"], ascending=[True, False, False])
               .drop_duplicates("k").set_index("k")["o"])
        tab = tab.str.capitalize().str.replace("Nevoeiro/neblina", "Nevoeiro/neblina")
        df[col] = df[col].map(tab).astype("string")
        df = df.drop(columns=[col + "__orig"])
    return df


def executar(raw_dir: str, out_dir: str) -> pd.DataFrame:
    os.makedirs(out_dir, exist_ok=True)
    arquivos = sorted(glob.glob(os.path.join(raw_dir, "datatran*.csv")))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum datatran*.csv em {raw_dir}")
    log: dict = {}
    partes = [tratar(ler_arquivo(a), log, os.path.basename(a)) for a in arquivos]
    df = pd.concat(partes, ignore_index=True)
    df = rotular_categorias(df)
    log["_total"] = {"linhas_finais": int(len(df)),
                     "anos": sorted(int(a) for a in df["ano"].dropna().unique())}
    df.to_csv(os.path.join(out_dir, "acidentes_prf_tratado.csv.gz"), index=False,
              compression="gzip")
    with open(os.path.join(out_dir, "etl_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return df


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--raw", default="data/raw")
    p.add_argument("--out", default="data/processed")
    a = p.parse_args()
    executar(a.raw, a.out)
