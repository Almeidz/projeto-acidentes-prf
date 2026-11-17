"""Figuras estáticas (matplotlib/seaborn) para notebook e artigo."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AZUL, LARANJA, CINZA, VERMELHO = "#1f77b4", "#d95f02", "#7f7f7f", "#b2182b"
plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 200, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 11})


def _fmt_milhar(x, _=None):
    return f"{x:,.0f}".replace(",", ".")


def fig_anual(anual: pd.DataFrame):
    """RQ1 – acidentes (barras) e mortos (linha), eixo duplo."""
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = anual["ano"].astype(str)
    ax.bar(x, anual["acidentes"], color=AZUL, alpha=.85, label="Acidentes")
    ax.set_ylabel("Acidentes registrados")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_milhar))
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(x, anual["mortos"], color=LARANJA, marker="o", lw=2, label="Mortos")
    ax2.set_ylabel("Mortos")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_milhar))
    ax2.set_ylim(0, anual["mortos"].max() * 1.15)
    ax.set_title("Acidentes e mortos em rodovias federais, 2007–2020 (sem 2019)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", frameon=False)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def fig_sem_vitimas(anual: pd.DataFrame, pct_sem_vitimas: pd.Series):
    """RQ1 – letalidade vs. participação de acidentes sem vítimas (ruptura de registro)."""
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = anual["ano"].astype(str)
    ax.plot(x, pct_sem_vitimas.values, color=CINZA, marker="s", lw=2,
            label="% de acidentes sem vítimas")
    ax.set_ylabel("% de acidentes sem vítimas")
    ax.set_ylim(0, 70)
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(x, anual["letalidade"], color=VERMELHO, marker="o", lw=2,
             label="Mortos por 100 acidentes")
    ax2.set_ylabel("Mortos por 100 acidentes")
    ax2.set_ylim(0, 10)
    ax.set_title("Letalidade sobe enquanto cai a parcela de acidentes sem vítimas")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", frameon=False)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def fig_causas(causas: pd.DataFrame):
    """RQ2 – mortos por grupo de causa e % de acidentes fatais."""
    c = causas.sort_values("mortos")
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True,
                            gridspec_kw={"width_ratios": [1.4, 1]})
    axs[0].barh(c["causa_grupo"], c["mortos"], color=AZUL)
    axs[0].set_xlabel("Mortos (2007–2020)")
    axs[0].xaxis.set_major_formatter(plt.FuncFormatter(_fmt_milhar))
    axs[0].set_title("Volume de mortes")
    axs[1].barh(c["causa_grupo"], c["pct_fatais"], color=LARANJA)
    axs[1].set_xlabel("% dos acidentes com morte")
    axs[1].set_title("Gravidade")
    fig.tight_layout()
    return fig


def fig_heatmap(h: pd.DataFrame):
    """RQ2 – mortos por dia da semana × hora."""
    fig, ax = plt.subplots(figsize=(10, 3.8))
    im = ax.imshow(h.values, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(len(h.index)), [d.capitalize() for d in h.index])
    ax.set_xticks(range(0, 24, 2), [f"{i:02d}h" for i in range(0, 24, 2)])
    ax.set_title("Mortos por dia da semana e hora do acidente (2007–2020)")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, pad=.01)
    cb.set_label("Mortos")
    fig.tight_layout()
    return fig


def fig_fase_clima(fase: pd.DataFrame, clima: pd.DataFrame):
    """RQ2 – % de acidentes fatais por fase do dia e por condição meteorológica."""
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [1, 1.3]})
    f = fase.sort_values("pct_fatais")
    axs[0].barh(f["fase_dia"], f["pct_fatais"], color=AZUL)
    axs[0].set_title("Por fase do dia")
    axs[0].set_xlabel("% de acidentes com morte")
    c = clima.sort_values("pct_fatais")
    axs[1].barh(c["condicao_meteorologica"], c["pct_fatais"], color=LARANJA)
    axs[1].set_title("Por condição meteorológica")
    axs[1].set_xlabel("% de acidentes com morte")
    fig.tight_layout()
    return fig


def fig_tipos(tipos: pd.DataFrame, topo: int = 8):
    t = tipos.head(topo).sort_values("pct_fatais")
    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    ax.barh(t["tipo_acidente"], t["pct_fatais"], color=VERMELHO)
    ax.set_xlabel("% de acidentes com morte")
    ax.set_title("Tipos de acidente mais letais (mín. 5 mil ocorrências)")
    fig.tight_layout()
    return fig


def fig_uf(uf: pd.DataFrame):
    """RQ3 – mortos por UF (barras) e letalidade (pontos)."""
    u = uf.sort_values("mortos", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(u["uf"], u["mortos"], color=AZUL)
    ax.set_ylabel("Mortos (2007–2020)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_milhar))
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(u["uf"], u["letalidade"], "o", color=LARANJA, ms=6)
    ax2.set_ylabel("Mortos por 100 acidentes")
    ax2.set_ylim(0, u["letalidade"].max() * 1.15)
    ax.set_title("Mortos (barras) e letalidade (pontos) por UF")
    fig.tight_layout()
    return fig


def fig_trechos(trechos: pd.DataFrame):
    t = trechos.sort_values("mortos")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(t["trecho"], t["mortos"], color=VERMELHO)
    ax.set_xlabel("Mortos (2007–2020)")
    ax.set_title("15 trechos de 10 km com mais mortes")
    fig.tight_layout()
    return fig


def salvar(fig, caminho: str) -> None:
    fig.savefig(caminho, bbox_inches="tight")
    plt.close(fig)
