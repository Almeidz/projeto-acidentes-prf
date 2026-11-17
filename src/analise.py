"""Funções de agregação usadas pelo notebook e pelo artigo (docs/index.html)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

ARQUIVO = "data/processed/acidentes_prf_tratado.csv.gz"
ORDEM_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def carregar(caminho: str = ARQUIVO) -> pd.DataFrame:
    df = pd.read_csv(caminho, low_memory=False, parse_dates=["data"],
                     dtype={"hora": "Int8", "ano": "Int16"})
    df["fatal"] = df["mortos"] > 0
    return df


def serie_anual(df: pd.DataFrame) -> pd.DataFrame:
    """RQ1: acidentes, mortos, feridos e letalidade (mortos por 100 acidentes) por ano."""
    g = df.groupby("ano").agg(acidentes=("id", "size"), mortos=("mortos", "sum"),
                              feridos=("feridos", "sum"), fatais=("fatal", "sum"),
                              veiculos=("veiculos", "sum"))
    g["letalidade"] = g["mortos"] / g["acidentes"] * 100
    g["pct_fatais"] = g["fatais"] / g["acidentes"] * 100
    return g.reset_index()


def por_causa(df: pd.DataFrame) -> pd.DataFrame:
    """RQ2: volume, mortos e letalidade por grupo de causa."""
    d = df.dropna(subset=["causa_grupo"])
    g = d.groupby("causa_grupo").agg(acidentes=("id", "size"), mortos=("mortos", "sum"),
                                     fatais=("fatal", "sum"))
    g["letalidade"] = g["mortos"] / g["acidentes"] * 100
    g["pct_fatais"] = g["fatais"] / g["acidentes"] * 100
    return g.sort_values("mortos", ascending=False).reset_index()


def por_tipo(df: pd.DataFrame, minimo: int = 5000) -> pd.DataFrame:
    g = df.groupby("tipo_acidente").agg(acidentes=("id", "size"), mortos=("mortos", "sum"),
                                        fatais=("fatal", "sum"))
    g = g[g["acidentes"] >= minimo].copy()
    g["pct_fatais"] = g["fatais"] / g["acidentes"] * 100
    return g.sort_values("pct_fatais", ascending=False).reset_index()


def heatmap_dia_hora(df: pd.DataFrame, metrica: str = "mortos") -> pd.DataFrame:
    d = df.dropna(subset=["dia_semana", "hora"])
    if metrica == "mortos":
        p = d.pivot_table(index="dia_semana", columns="hora", values="mortos", aggfunc="sum")
    else:
        p = d.pivot_table(index="dia_semana", columns="hora", values="id", aggfunc="size")
    return p.reindex(ORDEM_DIAS).fillna(0).astype(int)


def por_fase_dia(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["fase_dia"])
    g = d.groupby("fase_dia").agg(acidentes=("id", "size"), fatais=("fatal", "sum"),
                                  mortos=("mortos", "sum"))
    g["pct_fatais"] = g["fatais"] / g["acidentes"] * 100
    return g.reset_index()


def por_clima(df: pd.DataFrame) -> pd.DataFrame:
    d = df[~df["condicao_meteorologica"].isin(["Ignorada", "Ignorado"])].dropna(
        subset=["condicao_meteorologica"])
    g = d.groupby("condicao_meteorologica").agg(acidentes=("id", "size"),
                                                fatais=("fatal", "sum"))
    g = g[g["acidentes"] >= 1000].copy()
    g["pct_fatais"] = g["fatais"] / g["acidentes"] * 100
    return g.sort_values("pct_fatais", ascending=False).reset_index()


def por_uf(df: pd.DataFrame) -> pd.DataFrame:
    """RQ3 (nível UF)."""
    g = df.dropna(subset=["uf"]).groupby("uf").agg(
        acidentes=("id", "size"), mortos=("mortos", "sum"), fatais=("fatal", "sum"))
    g["letalidade"] = g["mortos"] / g["acidentes"] * 100
    g["pct_fatais"] = g["fatais"] / g["acidentes"] * 100
    return g.sort_values("mortos", ascending=False).reset_index()


def trechos_criticos(df: pd.DataFrame, janela_km: int = 10, topo: int = 15) -> pd.DataFrame:
    """RQ3 (nível trecho): agrupa por UF + BR + janela de km (ex.: km 100-109)."""
    d = df.dropna(subset=["uf", "br", "km"]).copy()
    d["janela"] = (d["km"] // janela_km * janela_km).astype(int)
    g = d.groupby(["uf", "br", "janela"]).agg(
        acidentes=("id", "size"), mortos=("mortos", "sum"),
        municipio=("municipio", lambda s: s.mode().iat[0])).reset_index()
    g["br"] = g["br"].astype(int)
    g["trecho"] = ("BR-" + g["br"].astype(str) + "/" + g["uf"] + " km "
                   + g["janela"].astype(str) + "–" + (g["janela"] + janela_km - 1).astype(str))
    return g.sort_values("mortos", ascending=False).head(topo).reset_index(drop=True)


def teste_qui2(df: pd.DataFrame, col: str) -> dict:
    """Qui-quadrado de independência entre `col` e acidente fatal (sim/não)."""
    d = df.dropna(subset=[col])
    tab = pd.crosstab(d[col], d["fatal"])
    chi2, p, gl, _ = stats.chi2_contingency(tab)
    n = tab.values.sum()
    v = float(np.sqrt(chi2 / (n * (min(tab.shape) - 1))))  # V de Cramér
    return {"chi2": float(chi2), "p": float(p), "gl": int(gl), "n": int(n), "cramer_v": v}


def resumo_numerico(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["pessoas", "veiculos", "mortos", "feridos"]
    r = df[cols].describe(percentiles=[.5, .95, .99]).T
    r["assimetria"] = df[cols].skew()
    return r
