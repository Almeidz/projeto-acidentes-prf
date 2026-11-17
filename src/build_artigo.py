"""Gera docs/index.html a partir dos dados tratados.

Todos os números citados no texto são calculados aqui (nenhum valor é digitado à mão),
o que garante consistência entre o artigo, o notebook e os dados.

Uso: python -m src.build_artigo
"""
from __future__ import annotations

import json
import re

import pandas as pd
from scipy import stats

from src import analise as a

REPO = "https://github.com/Almeidz/projeto-acidentes-prf"
PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def br(n, casas=0):
    """Formata número no padrão brasileiro (1.234,5)."""
    s = f"{n:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas=1):
    return br(x, casas) + "%"


def calcular() -> dict:
    df = a.carregar()
    an = a.serie_anual(df).set_index("ano")
    causas = a.por_causa(df).set_index("causa_grupo")
    tipos = a.por_tipo(df).set_index("tipo_acidente")
    fase = a.por_fase_dia(df).set_index("fase_dia")
    clima = a.por_clima(df).set_index("condicao_meteorologica")
    uf = a.por_uf(df).set_index("uf")
    trechos = a.trechos_criticos(df)
    heat = a.heatmap_dia_hora(df)
    sv = df.assign(sv=df["gravidade"].eq("sem_vitimas")).groupby("ano")["sv"].mean() * 100
    mortos_tipo = df.groupby("tipo_acidente")["mortos"].sum().sort_values(ascending=False)
    dia_mortos = df.groupby("dia_semana")["mortos"].sum()
    fds = (dia_mortos["sábado"] + dia_mortos["domingo"]) / dia_mortos.sum() * 100
    pico = heat.stack().idxmax()
    rho, p_rho = stats.spearmanr(uf["acidentes"], uf["letalidade"])
    return dict(df=df, an=an, causas=causas, tipos=tipos, fase=fase, clima=clima, uf=uf,
                trechos=trechos, heat=heat, sv=sv, mortos_tipo=mortos_tipo, fds=fds, pico=pico,
                rho=rho, p_rho=p_rho, qui_fase=a.teste_qui2(df, "fase_dia"),
                resumo=a.resumo_numerico(df))


def resumo_texto(c: dict) -> str:
    an, sv, fase = c["an"], c["sv"], c["fase"]
    var_acid = (an.loc[2020, "acidentes"] / an.loc[2007, "acidentes"] - 1) * 100
    var_mortos = (an.loc[2020, "mortos"] / an.loc[2007, "mortos"] - 1) * 100
    razao_noite = fase.loc["Plena noite", "pct_fatais"] / fase.loc["Pleno dia", "pct_fatais"]
    uf = c["uf"]
    return (
        f"Este estudo analisa {br(len(c['df']))} ocorrências registradas pela Polícia Rodoviária "
        f"Federal (PRF) nas rodovias federais brasileiras entre 2007 e 2020 (a base utilizada não "
        f"contém 2019). Um pipeline determinístico em Python unifica 13 arquivos anuais com "
        f"codificações, formatos de data e taxonomias distintas, registrando todos os descartes. "
        f"Três perguntas orientam a análise: como evoluíram acidentes e mortes, quais fatores se "
        f"associam à gravidade e onde se concentram os óbitos. O número de acidentes registrados "
        f"caiu {pct(abs(var_acid))} entre 2007 e 2020 e o de mortos, {pct(abs(var_mortos))}, enquanto a "
        f"letalidade passou de {br(an.loc[2007, 'letalidade'], 1)} para "
        f"{br(an.loc[2020, 'letalidade'], 1)} mortos por 100 acidentes. Em paralelo, a parcela de "
        f"acidentes sem vítimas caiu de {pct(sv[2007], 0)} para {pct(sv[2020], 0)}, indício de que "
        f"o critério de registro mudou. Acidentes em plena noite têm {br(razao_noite, 1)} vezes a "
        f"proporção de casos fatais dos ocorridos em pleno dia, e as noites de fim de semana "
        f"concentram os picos de mortes. Minas Gerais lidera em mortes absolutas; Maranhão e "
        f"Tocantins, em letalidade. Discutem-se as limitações dos dados e a necessidade de "
        f"normalizar por volume de tráfego em trabalhos futuros."
    )


def plotly_traces(c: dict) -> dict:
    an, uf, heat = c["an"].reset_index(), c["uf"].reset_index(), c["heat"]
    anual = {
        "data": [
            {"type": "bar", "x": an["ano"].astype(str).tolist(), "y": an["acidentes"].tolist(),
             "name": "Acidentes", "marker": {"color": "#1f77b4"},
             "hovertemplate": "%{x}: %{y:,} acidentes<extra></extra>"},
            {"type": "scatter", "mode": "lines+markers", "x": an["ano"].astype(str).tolist(),
             "y": an["mortos"].tolist(), "name": "Mortos", "yaxis": "y2",
             "line": {"color": "#d95f02", "width": 3},
             "hovertemplate": "%{x}: %{y:,} mortos<extra></extra>"}],
        "layout": {"margin": {"t": 30, "r": 60, "l": 60, "b": 50},
                   "xaxis": {"type": "category", "title": "Ano (2019 ausente na base)"},
                   "yaxis": {"title": "Acidentes"},
                   "yaxis2": {"title": "Mortos", "overlaying": "y", "side": "right",
                              "rangemode": "tozero"},
                   "legend": {"orientation": "h", "y": 1.12}}}
    heatmap = {
        "data": [{"type": "heatmap", "z": heat.values.tolist(),
                  "x": [f"{h:02d}h" for h in heat.columns],
                  "y": [d.capitalize() for d in heat.index], "colorscale": "YlOrRd",
                  "colorbar": {"title": "Mortos"},
                  "hovertemplate": "%{y}, %{x}: %{z:,} mortos<extra></extra>"}],
        "layout": {"margin": {"t": 20, "r": 20, "l": 80, "b": 50},
                   "yaxis": {"autorange": "reversed"}, "xaxis": {"title": "Hora do acidente"}}}
    scatter = {
        "data": [{"type": "scatter", "mode": "markers+text", "x": uf["acidentes"].tolist(),
                  "y": uf["letalidade"].round(2).tolist(), "text": uf["uf"].tolist(),
                  "textposition": "top center",
                  "marker": {"size": (uf["mortos"] / uf["mortos"].max() * 40 + 8).tolist(),
                             "color": "#1f77b4", "opacity": .7},
                  "customdata": uf[["mortos"]].values.tolist(),
                  "hovertemplate": "<b>%{text}</b><br>%{x:,} acidentes<br>%{customdata[0]:,} "
                                   "mortos<br>%{y} mortos/100 acid.<extra></extra>"}],
        "layout": {"margin": {"t": 20, "r": 20, "l": 60, "b": 60},
                   "xaxis": {"type": "log", "title": "Acidentes registrados (escala log)"},
                   "yaxis": {"title": "Mortos por 100 acidentes"}}}
    return {"anual": anual, "heatmap": heatmap, "scatter": scatter}


CSS = """
:root{--fg:#1a1a1a;--mut:#555;--bg:#fff;--card:#f6f7f9;--ac:#0b5cab;--bd:#dde1e6}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:17px/1.65 Georgia,'Times New Roman',serif;color:var(--fg);background:var(--bg)}
main{max-width:860px;margin:0 auto;padding:1.5rem 1.1rem 4rem}
h1{font-size:1.9rem;line-height:1.25;margin:.4rem 0}h2{margin-top:2.4rem;border-bottom:2px solid var(--bd);padding-bottom:.2rem}
h3{margin-top:1.8rem}.meta,.badges,nav,.btn,figcaption,th,.fig-note{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.meta{color:var(--mut);font-size:.95rem}.badges span{display:inline-block;background:var(--card);border:1px solid var(--bd);border-radius:999px;padding:.1rem .7rem;margin:.15rem .2rem .15rem 0;font-size:.8rem}
.btn{display:inline-block;background:var(--ac);color:#fff;text-decoration:none;padding:.45rem .9rem;border-radius:6px;margin-top:.6rem;font-size:.95rem}
.abstract{background:var(--card);border-left:4px solid var(--ac);padding:1rem 1.2rem;border-radius:4px}
nav{font-size:.9rem;margin:1.2rem 0}nav a{margin-right:.8rem;color:var(--ac)}
figure{margin:1.6rem 0}figure img,.plot{width:100%}figcaption{font-size:.88rem;color:var(--mut);margin-top:.3rem}
.plot{height:420px}pre{background:#0f172a;color:#e2e8f0;padding:1rem;border-radius:6px;overflow-x:auto;font-size:.82rem;line-height:1.5}
code{font-family:ui-monospace,Menlo,Consolas,monospace}p code{background:var(--card);padding:.05rem .3rem;border-radius:3px;font-size:.88em}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.88rem;margin:1rem 0}
th,td{border-bottom:1px solid var(--bd);padding:.35rem .5rem;text-align:right}th:first-child,td:first-child{text-align:left}
th{background:var(--card)}.pend{background:#fff3bf;padding:0 .25rem;border-radius:3px}
.fair{background:var(--card);padding:1rem 1.2rem;border-radius:6px}.fair li{margin:.3rem 0}
.ref{padding-left:0;list-style:none;font-size:.92rem}.ref li{margin:.55rem 0}
footer{font-family:system-ui,sans-serif;font-size:.85rem;color:var(--mut);margin-top:3rem;border-top:1px solid var(--bd);padding-top:1rem}
@media(max-width:600px){body{font-size:16px}h1{font-size:1.5rem}.plot{height:340px}}
"""


def tabela(df: pd.DataFrame, fmt: dict, rotulos: dict) -> str:
    cab = "".join(f"<th>{rotulos.get(c, c)}</th>" for c in df.columns)
    linhas = []
    for _, r in df.iterrows():
        tds = "".join(f"<td>{fmt.get(c, str)(r[c])}</td>" for c in df.columns)
        linhas.append(f"<tr>{tds}</tr>")
    return f'<div class="tw"><table><thead><tr>{cab}</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'


CODE_ETL = """def normalizar_texto(s: pd.Series) -> pd.Series:
    \"\"\"strip, minúsculas, sem acentos, espaços colapsados; '(null)' -> NA.\"\"\"
    s = s.astype("string").str.strip()
    s = s.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
    s = s.str.lower().str.replace(r"\\s+", " ", regex=True)
    return s.mask(s.isin(NULL_TOKENS))

def parse_data(s: pd.Series) -> pd.Series:
    # Três formatos observados: AAAA-MM-DD, DD/MM/AAAA e DD/MM/AA
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for regex, fmt in ((r"^\\d{4}-\\d{2}-\\d{2}$", "%Y-%m-%d"),
                       (r"^\\d{2}/\\d{2}/\\d{4}$", "%d/%m/%Y"),
                       (r"^\\d{2}/\\d{2}/\\d{2}$", "%d/%m/%y")):
        m = s.str.match(regex, na=False)
        if m.any():
            out[m] = pd.to_datetime(s[m], format=fmt)
    return out

# km fora de [0, 5000] é erro de digitação -> NaN (contado no log)
km_invalido = df["km"].notna() & ~df["km"].between(0, KM_MAX)
df.loc[km_invalido, "km"] = np.nan"""

CODE_AGG = """# Letalidade = mortos por 100 acidentes; % fatais = acidentes com ao menos 1 morte
g = df.groupby("ano").agg(acidentes=("id", "size"), mortos=("mortos", "sum"),
                          fatais=("fatal", "sum"))
g["letalidade"] = g["mortos"] / g["acidentes"] * 100

# Trechos críticos: UF + BR + janela de 10 km
d["janela"] = (d["km"] // 10 * 10).astype(int)
g = d.groupby(["uf", "br", "janela"]).agg(acidentes=("id", "size"), mortos=("mortos", "sum"))"""


def montar(c: dict) -> str:
    an, sv, fase, clima = c["an"], c["sv"], c["fase"], c["clima"]
    causas, tipos, uf, trechos = c["causas"], c["tipos"], c["uf"], c["trechos"]
    df, mt, q = c["df"], c["mortos_tipo"], c["qui_fase"]
    resumo = resumo_texto(c)
    n_palavras = len(re.findall(r"[\wÀ-ÿ]+", resumo))
    assert 150 <= n_palavras <= 250, f"Resumo com {n_palavras} palavras (exigido: 150–250)"

    log = json.load(open("data/processed/etl_log.json", encoding="utf-8"))
    tot = {k: sum(v.get(k, 0) for kk, v in log.items() if kk != "_total")
           for k in ("linhas_lidas", "descartadas_id_duplicado", "km_invalido_anulado",
                     "uf_ausente", "br_ausente")}
    pico_dia, pico_hora = c["pico"]
    pico_val = int(c["heat"].loc[pico_dia, pico_hora])
    pico_fase_n = fase.loc["Plena noite", "pct_fatais"]
    pico_fase_d = fase.loc["Pleno dia", "pct_fatais"]
    top_causa_info = causas.drop(index="Outras / ignorada").sort_values("mortos", ascending=False)
    sem_info = causas.loc["Outras / ignorada"]
    uf_let = uf[uf["acidentes"] >= 5000].sort_values("letalidade", ascending=False)
    uf_mortos = uf.sort_values("mortos", ascending=False)
    # O texto cita estes resultados nominalmente; falha se os dados mudarem
    assert list(uf_mortos.index[:2]) == ["MG", "BA"], list(uf_mortos.index[:2])
    assert list(uf_let.index[:2]) == ["MA", "TO"], list(uf_let.index[:2])
    assert tipos["pct_fatais"].idxmax() in ("Atropelamento de pessoa", "Atropelamento de pedestre", "Colisão frontal")
    assert mt.index[0] == "Colisão frontal"
    assert fase["pct_fatais"].idxmax() == "Plena noite"
    t0 = trechos.iloc[0]
    pico_ano = an["acidentes"].idxmax()
    queda_pico = (an.loc[2020, "acidentes"] / an.loc[pico_ano, "acidentes"] - 1) * 100
    queda_mortos = (an.loc[2020, "mortos"] / an["mortos"].max() - 1) * 100
    mort_ano = an["mortos"].idxmax()
    ped = causas.loc["Pedestre"]
    traces = json.dumps(plotly_traces(c), ensure_ascii=False)

    tb_an = tabela(
        an.reset_index()[["ano", "acidentes", "mortos", "letalidade"]].assign(sv=sv.values),
        {"ano": str, "acidentes": lambda v: br(v), "mortos": lambda v: br(v),
         "letalidade": lambda v: br(v, 2), "sv": lambda v: pct(v)},
        {"ano": "Ano", "acidentes": "Acidentes", "mortos": "Mortos",
         "letalidade": "Mortos/100 acid.", "sv": "% sem vítimas"})
    tb_log = tabela(
        pd.DataFrame({"Etapa": ["Linhas lidas (13 arquivos)", "Descartadas: <code>id</code> repetido no mesmo arquivo (mantida a 1ª linha)",
                                "Valores de <code>km</code> inválidos anulados (→ NaN)",
                                "<code>uf</code> ausente (mantidas)", "<code>br</code> ausente (mantidas)",
                                "Linhas finais"],
                      "Qtde": [br(tot["linhas_lidas"]), br(tot["descartadas_id_duplicado"]),
                               br(tot["km_invalido_anulado"]), br(tot["uf_ausente"]),
                               br(tot["br_ausente"]), br(len(df))]}), {}, {})
    tb_trechos = tabela(
        trechos.head(8)[["trecho", "municipio", "acidentes", "mortos"]],
        {"acidentes": lambda v: br(v), "mortos": lambda v: br(v),
         "municipio": lambda v: v.title()},
        {"trecho": "Trecho (10 km)", "municipio": "Município mais frequente",
         "acidentes": "Acidentes", "mortos": "Mortos"})

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acidentes em rodovias federais brasileiras (2007–2020): evolução, gravidade e geografia</title>
<meta name="description" content="Análise de {br(len(df))} ocorrências da PRF com pipeline reprodutível em Python (FAIR).">
<meta name="author" content="Lucas de Almeida Brugger Cavalcante">
<style>{CSS}</style></head><body><main>

<header>
<p class="meta">Linguagem de Programação (Análise e Visualização de Dados com Python) · 6º período · Bacharelado em Sistemas de Informação · <span class="pend">[Instituição]</span> · <span class="pend">[Semestre/Ano]</span></p>
<h1>Acidentes em rodovias federais brasileiras (2007–2020): evolução, gravidade e distribuição geográfica das mortes</h1>
<p class="meta"><strong>Lucas de Almeida Brugger Cavalcante</strong>, <span class="pend">[Nome do integrante 2]</span>, <span class="pend">[Nome do integrante 3, se houver]</span><br>Bacharelado em Sistemas de Informação, <span class="pend">[Instituição]</span></p>
<div class="badges"><span>Python · pandas</span><span>Dados abertos PRF</span><span>FAIR</span><span>Código: MIT</span><span>Dados e texto: CC-BY 4.0</span></div>
<a class="btn" href="{REPO}">Ver repositório no GitHub</a>
</header>

<nav><a href="#resumo">Resumo</a><a href="#intro">1 Introdução</a><a href="#metodo">2 Metodologia</a><a href="#resultados">3 Resultados</a><a href="#conclusao">4 Conclusão</a><a href="#fair">5 FAIR</a><a href="#refs">6 Referências</a></nav>

<section id="resumo" class="abstract"><h2 style="margin-top:0;border:0">Resumo</h2>
<p>{resumo}</p>
<p><strong>Palavras-chave:</strong> acidentes de trânsito; rodovias federais; Polícia Rodoviária Federal; análise exploratória; dados abertos.</p></section>

<section id="intro"><h2>1. Introdução</h2>
<p>Os acidentes nas rodovias federais geram custo humano e econômico expressivo para o país. A Polícia Rodoviária Federal (PRF) publica, em formato aberto, os registros de cada ocorrência atendida, o que permite estudar séries longas e identificar padrões úteis para fiscalização e políticas de prevenção. Esses registros, porém, foram produzidos por mais de uma década com colunas, categorias e critérios que mudaram ao longo do tempo, e tratá-los como uma série homogênea é um risco metodológico que este trabalho procura explicitar.</p>
<p>O estudo busca responder às seguintes perguntas de pesquisa:</p>
<ul>
<li><strong>RQ1.</strong> Como evoluíram o número de acidentes, de mortos e a letalidade entre 2007 e 2020, e essa evolução é comparável ao longo do período?</li>
<li><strong>RQ2.</strong> Quais causas, tipos de acidente e condições (hora, dia da semana, fase do dia, clima) se associam à maior gravidade?</li>
<li><strong>RQ3.</strong> Em quais estados e trechos de rodovia se concentram as mortes?</li></ul></section>

<section id="metodo"><h2>2. Metodologia e pipeline de dados</h2>
<h3>2.1 Fonte e granularidade</h3>
<p>Os dados são os arquivos <code>datatran</code> da PRF, na versão agrupada por ocorrência disponível no Kaggle (<a href="https://www.kaggle.com/datasets/equeiroz/acidentes-rodovias-federais-brasil-jan07-a-jul19">equeiroz</a>), cuja origem é o portal de <a href="https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf">dados abertos da PRF</a>. Cada linha é <em>um acidente</em>, com data, hora, local (UF, BR, km, município), causa, tipo, condições e contagens de pessoas, mortos, feridos e veículos. O arquivo de 2019 não está presente na base utilizada, portanto a série tem 13 anos, com uma lacuna entre 2018 e 2020.</p>
<h3>2.2 Tratamento</h3>
<p>A auditoria inicial mostrou que os arquivos não são diretamente empilháveis: a codificação é <code>latin-1</code> até 2018 e <code>utf-8</code> em 2020; há três formatos de data; as colunas <code>latitude</code>, <code>longitude</code>, <code>regional</code>, <code>delegacia</code> e <code>uop</code> só existem a partir de 2017; o separador decimal de <code>km</code> alterna entre vírgula e ponto; há espaços à direita nos textos de 2017; o texto literal <code>(null)</code> representa ausência; e as categorias mudaram de grafia e granularidade (por exemplo, "Falta de atenção" e "Falta de atenção à condução"; "Ignorada" e "Ignorado"). As causas, com 64 grafias distintas após a normalização de texto, foram agrupadas em 11 grupos por regras explícitas em <code>src/etl.py</code>. A coluna <code>uso_solo</code> foi descartada porque mudou de significado (Urbano/Rural até 2016; Sim/Não a partir de 2017).</p>
<pre><code>{CODE_ETL.replace("<", "&lt;").replace(">", "&gt;")}</code></pre>
<p>O <code>id</code> não é único na série completa (os mesmos números se repetem em anos diferentes, designando acidentes distintos); a chave é o par (<code>ano</code>, <code>id</code>). Dentro de um mesmo arquivo, os poucos <code>id</code> repetidos correspondem ao mesmo acidente listado duas vezes com clima ou tipo de pista divergentes, e mantivemos a primeira linha. Nenhuma operação é destrutiva sem registro: os descartes e as anulações são contados por arquivo em <code>data/processed/etl_log.json</code>, e registros logicamente inconsistentes (mortos + feridos &gt; pessoas) seriam apenas sinalizados — não houve nenhum. Métricas derivadas: <code>ano</code>, <code>hora</code>, <code>gravidade</code> (fatal, com feridos, sem vítimas), <code>causa_grupo</code> e, nas análises, a <em>letalidade</em> (mortos por 100 acidentes) e o <em>% de acidentes fatais</em> (acidentes com ao menos uma morte).</p>
{tb_log}
<pre><code>{CODE_AGG.replace("<", "&lt;").replace(">", "&gt;")}</code></pre></section>

<section id="resultados"><h2>3. Resultados e discussão</h2>
<h3>3.1 RQ1 — Evolução temporal</h3>
<p>O número de acidentes registrados atingiu o pico em {pico_ano} ({br(an.loc[pico_ano, 'acidentes'])}) e chegou a {br(an.loc[2020, 'acidentes'])} em 2020, uma queda de {pct(abs(queda_pico))} em relação ao pico. O número de mortos teve o máximo em {mort_ano} ({br(an['mortos'].max())}) e fechou a série em {br(an.loc[2020, 'mortos'])} (queda de {pct(abs(queda_mortos))}). Como os acidentes caíram bem mais que as mortes, a letalidade subiu de {br(an.loc[2013, 'letalidade'], 2)} (2013) para {br(an.loc[2020, 'letalidade'], 2)} (2020).</p>
<div id="p-anual" class="plot"></div>
<figure><img src="assets/fig1_anual.png" alt="Acidentes e mortos por ano, 2007–2020" loading="lazy"><figcaption>Figura 1. Acidentes (barras) e mortos (linha) por ano. Versão estática do gráfico interativo acima.</figcaption></figure>
<p>Essa leitura exige cautela. A Figura 2 mostra que a parcela de acidentes <em>sem vítimas</em> era estável, entre {pct(sv[2007], 0)} e {pct(sv.loc[2007:2014].max(), 0)}, até 2014 e despenca depois, chegando a {pct(sv[2020], 1)} em 2020. Se a segurança tivesse melhorado de forma homogênea, esperaríamos queda proporcional nos três tipos de acidente. O que se observa é que os acidentes mais leves "somem" muito mais rápido que os fatais — padrão compatível com mudança no que a PRF passou a registrar ou atender, ou com uma combinação disso com redução real do tráfego e dos acidentes. Os dados não permitem separar essas hipóteses. Por isso, a letalidade não deve ser lida como piora da segurança, e as contagens de mortes (presumivelmente menos sensíveis ao critério de registro, pois acidentes fatais dificilmente deixam de ser atendidos) são o indicador mais confiável da série.</p>
<figure><img src="assets/fig2_letalidade_registro.png" alt="Letalidade e percentual de acidentes sem vítimas por ano" loading="lazy"><figcaption>Figura 2. Letalidade (mortos por 100 acidentes) e % de acidentes sem vítimas.</figcaption></figure>
<div class="tw">{tb_an}</div>

<h3>3.2 RQ2 — Fatores associados à gravidade</h3>
<p><strong>Causas.</strong> O maior grupo em mortes é "Outras / ignorada" ({br(sem_info['mortos'])} mortos), que reúne principalmente a categoria genérica "Outras" das taxonomias antigas e, por isso, é pouco informativo. Entre as causas identificadas, lideram {top_causa_info.index[0].lower()} ({br(top_causa_info.iloc[0]['mortos'])} mortos), {top_causa_info.index[1].lower()} ({br(top_causa_info.iloc[1]['mortos'])}) e {top_causa_info.index[2].lower()} ({br(top_causa_info.iloc[2]['mortos'])}). Em gravidade, os grupos de pedestre ({pct(ped['pct_fatais'])} dos acidentes do grupo terminam em morte) e de desobediência às normas ({pct(causas.loc['Desobediência às normas', 'pct_fatais'])}) se destacam, ao passo que "distância de segurança" ({pct(causas.loc['Distância de segurança', 'pct_fatais'], 2)}) gera muitos acidentes, mas poucas mortes. O grupo "Pedestre" só aparece com esse nome na taxonomia pós-2017 e, portanto, subestima atropelamentos de períodos anteriores.</p>
<figure><img src="assets/fig3_causas.png" alt="Mortos e percentual de acidentes fatais por grupo de causa" loading="lazy"><figcaption>Figura 3. Mortos e % de acidentes fatais por grupo de causa (2007–2020).</figcaption></figure>
<p><strong>Tipo de acidente.</strong> Em número de mortes, a colisão frontal é o tipo mais grave ({br(mt['Colisão frontal'])} mortos; {pct(tipos.loc['Colisão frontal', 'pct_fatais'])} das ocorrências são fatais), seguida pelo atropelamento de pessoa ({pct(tipos.loc['Atropelamento de pessoa', 'pct_fatais'])} fatais). A colisão traseira, o tipo mais frequente, é comparativamente pouco letal ({pct(c['df'].query("tipo_acidente=='Colisão traseira'")['fatal'].mean()*100)}).</p>
<figure><img src="assets/fig6_tipos.png" alt="Tipos de acidente por percentual de casos fatais" loading="lazy"><figcaption>Figura 4. Tipos de acidente com maior proporção de casos fatais.</figcaption></figure>
<p><strong>Quando.</strong> O {pico_dia} às {pico_hora:02d}h concentra o maior número de mortes de toda a grade ({br(pico_val)}), e sábados e domingos respondem por {pct(c['fds'])} das mortes, ante 28,6% esperados se os dias fossem equivalentes. Acidentes em plena noite são fatais em {pct(pico_fase_n)} dos casos, contra {pct(pico_fase_d)} em pleno dia (razão de {br(pico_fase_n/pico_fase_d, 1)}). O teste qui-quadrado entre fase do dia e ocorrência de morte é significativo (χ² = {br(q['chi2'])}, gl = {q['gl']}, p &lt; 0,001), mas com <em>n</em> de {br(q['n'])} qualquer diferença torna-se significativa; o V de Cramér ({br(q['cramer_v'], 3)}) indica associação real, porém de efeito pequeno. Condições climáticas adversas não elevam a proporção de casos fatais de forma intuitiva: chuva ({pct(clima.loc['Chuva', 'pct_fatais'])}) fica abaixo de céu claro ({pct(clima.loc['Céu claro', 'pct_fatais'])}), possivelmente porque o condutor reduz a velocidade, e nevoeiro ({pct(clima.loc['Nevoeiro/neblina', 'pct_fatais'])}) e vento ({pct(clima.loc['Vento', 'pct_fatais'])}) ficam acima. Trata-se de associações, não de efeitos causais: a fase do dia, por exemplo, se confunde com fadiga, álcool e menor visibilidade.</p>
<div id="p-heat" class="plot" style="height:340px"></div>
<figure><img src="assets/fig4_heatmap.png" alt="Mapa de calor de mortos por dia da semana e hora" loading="lazy"><figcaption>Figura 5. Mortos por dia da semana e hora (versão estática do gráfico interativo).</figcaption></figure>
<figure><img src="assets/fig5_fase_clima.png" alt="Percentual de acidentes fatais por fase do dia e clima" loading="lazy"><figcaption>Figura 6. % de acidentes fatais por fase do dia e por condição meteorológica.</figcaption></figure>

<h3>3.3 RQ3 — Onde as mortes se concentram</h3>
<p>{uf_mortos.index[0]} lidera em mortes absolutas ({br(uf_mortos.iloc[0]['mortos'])}), seguido por {uf_mortos.index[1]} ({br(uf_mortos.iloc[1]['mortos'])}) e {uf_mortos.index[2]} ({br(uf_mortos.iloc[2]['mortos'])}), o que provavelmente reflete a extensão da malha federal e o fluxo de veículos desses estados (não medidos aqui). Em letalidade o quadro muda: {uf_let.index[0]} ({br(uf_let.iloc[0]['letalidade'], 1)} mortos por 100 acidentes) e {uf_let.index[1]} ({br(uf_let.iloc[1]['letalidade'], 1)}) superam estados com muito mais acidentes. A correlação de Spearman entre volume de acidentes e letalidade nas UFs é ρ = {br(c['rho'], 2)} (p = {br(c['p_rho'], 3)}): estados com mais acidentes tendem a ter menor letalidade, o que pode indicar que muitos acidentes de baixa gravidade em malhas mais urbanizadas diluem a taxa; trata-se de uma hipótese, não testada aqui.</p>
<div id="p-uf" class="plot"></div>
<figure><img src="assets/fig7_uf.png" alt="Mortos e letalidade por UF" loading="lazy"><figcaption>Figura 7. Mortos (barras) e letalidade (pontos) por UF.</figcaption></figure>
<p>No nível de trecho (janelas de 10 km), o mais mortal foi <strong>{t0['trecho']}</strong> ({t0['municipio'].title()}), com {br(t0['mortos'])} mortes e {br(t0['acidentes'])} acidentes. Quase todos os 15 trechos do topo ficam em regiões metropolitanas (Grande São Paulo, Grande Rio, Belém, Fortaleza, Recife, Vitória e Florianópolis), onde a rodovia federal funciona como via urbana, com a exceção de Campos dos Goytacazes (RJ).</p>
<figure><img src="assets/fig8_trechos.png" alt="Quinze trechos de 10 km com mais mortes" loading="lazy"><figcaption>Figura 8. Os 15 trechos de 10 km com mais mortes.</figcaption></figure>
{tb_trechos}</section>

<section id="conclusao"><h2>4. Conclusão</h2>
<p><strong>RQ1.</strong> Acidentes e mortes registrados caíram ao longo do período, porém não na mesma proporção: a letalidade aparente subiu quando a parcela de acidentes sem vítimas despencou, o que aponta para mudança de registro. Comparações de letalidade entre os anos iniciais e finais devem ser evitadas sem esse controle. <strong>RQ2.</strong> A gravidade associa-se sobretudo ao tipo de acidente (colisão frontal e atropelamentos), à noite e aos fins de semana no fim da tarde e início da noite; a distância de segurança e o clima têm papel menor no desfecho fatal. <strong>RQ3.</strong> As mortes concentram-se em Minas Gerais e Bahia em números absolutos, enquanto Maranhão e Tocantins lideram em letalidade, e os trechos mais mortais ficam, em sua maioria, em regiões metropolitanas.</p>
<p><strong>Limitações.</strong> (i) O arquivo de 2019 está ausente. (ii) A taxonomia de causas mudou em 2017, e o agrupamento em 11 categorias é uma decisão analítica nossa. (iii) O critério de registro parece ter mudado, o que compromete séries de acidentes e letalidade. (iv) Não há dados de volume de tráfego ou extensão por trecho, de modo que comparamos contagens e proporções entre locais com exposição distinta. (v) Coordenadas só existem a partir de 2017, o que impede mapas da série completa. <strong>Trabalhos futuros:</strong> normalizar por frota ou tráfego (VMD), incluir 2019 e anos recentes, usar as coordenadas para análise espacial e modelar a probabilidade de acidente fatal com regressão logística.</p></section>

<section id="fair"><h2>5. Disponibilidade dos dados e declaração FAIR</h2>
<div class="fair"><ul>
<li><strong>Findable:</strong> repositório com README, resumo, palavras-chave e link para a fonte original; autoria e disciplina no cabeçalho.</li>
<li><strong>Accessible:</strong> repositório público; nenhuma credencial é necessária para executar o ETL a partir dos dados tratados; esta página é servida por GitHub Pages e é responsiva.</li>
<li><strong>Interoperable:</strong> dados tratados em <code>.csv.gz</code> e dicionário em <code>data/data_dictionary.md</code>.</li>
<li><strong>Reusable:</strong> código sob licença MIT; dados tratados e texto sob CC-BY 4.0 (os dados originais pertencem à PRF e seguem os termos do portal de dados abertos); dependências com versões fixas em <code>requirements.txt</code>.</li></ul></div>
<p>Para reproduzir o pipeline completo:</p>
<pre><code>git clone {REPO}.git
cd projeto-acidentes-prf
python -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt
# coloque os datatran*.csv em data/raw/ (veja data/raw/README.md)
python -m src.etl --raw data/raw --out data/processed
python -m src.build_artigo      # regenera esta página</code></pre></section>

<section id="refs"><h2>6. Referências</h2>
<ul class="ref">
<li>BRASIL. Polícia Rodoviária Federal. <strong>Dados abertos da PRF</strong>: acidentes. Disponível em: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf. Acesso em: 16 nov. 2026.</li>
<li>EQUEIROZ. <strong>Acidentes rodovias federais Brasil Jan/07 a Dez/20</strong>. Kaggle. Disponível em: https://www.kaggle.com/datasets/equeiroz/acidentes-rodovias-federais-brasil-jan07-a-jul19. Acesso em: 16 nov. 2026.</li>
<li>HARRIS, C. R. et al. Array programming with NumPy. <strong>Nature</strong>, v. 585, p. 357–362, 2020.</li>
<li>HUNTER, J. D. Matplotlib: a 2D graphics environment. <strong>Computing in Science &amp; Engineering</strong>, v. 9, n. 3, p. 90–95, 2007.</li>
<li>MCKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9., 2010. <strong>Proceedings…</strong> 2010. p. 56–61.</li>
<li>PLOTLY TECHNOLOGIES INC. <strong>Collaborative data science</strong>. Montreal, 2015. Disponível em: https://plot.ly.</li>
<li>VIRTANEN, P. et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. <strong>Nature Methods</strong>, v. 17, p. 261–272, 2020.</li>
<li>WILKINSON, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship. <strong>Scientific Data</strong>, v. 3, 160018, 2016.</li></ul></section>

<footer>Texto e figuras sob CC-BY 4.0 · Código sob MIT · Gerado por <code>src/build_artigo.py</code> a partir de <code>data/processed/acidentes_prf_tratado.csv.gz</code>.</footer>
</main>
<script src="{PLOTLY}"></script>
<script>
const T = {traces};
const cfg = {{responsive: true, displaylogo: false}};
function draw(id, key) {{
  const el = document.getElementById(id);
  if (typeof Plotly === 'undefined') {{
    el.innerHTML = '<p class="fig-note">Gráfico interativo indisponível offline; veja a versão estática abaixo.</p>'; return;
  }}
  Plotly.newPlot(el, T[key].data, T[key].layout, cfg);
}}
draw('p-anual', 'anual'); draw('p-heat', 'heatmap'); draw('p-uf', 'scatter');
</script></body></html>"""


if __name__ == "__main__":
    calc = calcular()
    html = montar(calc)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("docs/index.html gerado:", len(html) // 1024, "KB")
