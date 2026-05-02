"""
ITBI SP Dashboard — Streamlit application
Reads from DuckDB Gold tables in read-only mode.
Contract version: v1.0 (2026-05-01)
"""

import os
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Dashboard ITBI São Paulo 2026",
    page_icon="🏙️",
    layout="wide",
)

MONTH_PT = {
    "2026-01": "Janeiro/2026",
    "2026-02": "Fevereiro/2026",
    "2026-03": "Março/2026",
    "2026-04": "Abril/2026",
    "2026-05": "Maio/2026",
    "2026-06": "Junho/2026",
    "2026-07": "Julho/2026",
    "2026-08": "Agosto/2026",
    "2026-09": "Setembro/2026",
    "2026-10": "Outubro/2026",
    "2026-11": "Novembro/2026",
    "2026-12": "Dezembro/2026",
}


def format_month_pt(month_year: str) -> str:
    return MONTH_PT.get(month_year, month_year)


def format_brl(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"R$ {value:,.0f}"


def format_pct(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

@st.cache_resource
def get_connection():
    db_path = os.environ.get("DB_PATH")
    if not db_path:
        st.error("DB_PATH not set. Run `make pipeline` first.")
        st.stop()
    if not Path(db_path).exists():
        st.error(f"Database not found at {db_path}. Run `make pipeline` first.")
        st.stop()
    return duckdb.connect(db_path, read_only=True)


@st.cache_data(ttl=3600)
def query(sql: str, params: list = None) -> pd.DataFrame:
    con = get_connection()
    if params:
        return con.execute(sql, params).df()
    return con.execute(sql).df()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.title("Controles")

    months_df = query("SELECT month_year FROM gold_itbi_monthly_summary ORDER BY month_year")
    months = months_df["month_year"].tolist()
    months_pt = [format_month_pt(m) for m in months]

    if len(months) < 2:
        start_month = months[0] if months else None
        end_month = months[-1] if months else None
    else:
        selected = st.sidebar.select_slider(
            "Período de análise",
            options=months_pt,
            value=(months_pt[0], months_pt[-1]),
        )
        start_month = months[months_pt.index(selected[0])]
        end_month = months[months_pt.index(selected[1])]

    min_tx_filter = st.sidebar.toggle(
        "Ocultar bairros com menos de 3 transações/mês",
        value=True,
    )

    # Freshness notice
    freshness_df = query("SELECT MAX(ingested_at) AS last_ingested FROM bronze_itbi_transactions")
    last_ingested = freshness_df["last_ingested"].iloc[0]
    if last_ingested is not None:
        st.sidebar.caption(
            f"Dados atualizados em: {pd.Timestamp(last_ingested).strftime('%d/%m/%Y %H:%M')} UTC  \n"
            "Fonte: Prefeitura de SP (ITBI declarado)"
        )

    return start_month, end_month, min_tx_filter


# ---------------------------------------------------------------------------
# Section A — City-wide Trends
# ---------------------------------------------------------------------------

def render_section_a(start_month: str, end_month: str):
    st.header("A. Evolução Citywide")

    df = query(
        """
        SELECT month_year, transaction_count, total_value_brl,
               kpi_median_price, kpi_median_price_per_m2, avg_price_per_m2
        FROM gold_itbi_monthly_summary
        WHERE month_year BETWEEN ? AND ?
        ORDER BY month_year
        """,
        [start_month, end_month],
    )

    if df.empty:
        st.info("Nenhum dado disponível para o período selecionado.")
        return

    df["month_pt"] = df["month_year"].apply(format_month_pt)

    # MoM calculations in Python
    df["mom_price_pct"] = df["kpi_median_price"].pct_change() * 100
    df["mom_m2_pct"] = df["kpi_median_price_per_m2"].pct_change() * 100

    # Metric cards
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    col1, col2, col3 = st.columns(3)
    with col1:
        delta_price = f"{last['mom_price_pct']:+.1f}%" if prev is not None and not pd.isna(last["mom_price_pct"]) else None
        st.metric(
            "Mediana de Preço (último mês)",
            format_brl(last["kpi_median_price"]),
            delta=delta_price,
        )
    with col2:
        delta_m2 = f"{last['mom_m2_pct']:+.1f}%" if prev is not None and not pd.isna(last["mom_m2_pct"]) else None
        st.metric(
            "Mediana Preço/m² (último mês)",
            f"{format_brl(last['kpi_median_price_per_m2'])}/m²",
            delta=delta_m2,
        )
    with col3:
        st.metric(
            "Total de Transações (período)",
            f"{int(df['transaction_count'].sum()):,}",
        )

    # Chart A1 — Median price + volume
    fig_a1 = go.Figure()
    fig_a1.add_trace(go.Bar(
        x=df["month_pt"],
        y=df["transaction_count"],
        name="Transações",
        yaxis="y2",
        marker_color="lightgrey",
        opacity=0.4,
    ))
    fig_a1.add_trace(go.Scatter(
        x=df["month_pt"],
        y=df["kpi_median_price"],
        mode="lines+markers",
        name="Mediana Preço",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=8),
        hovertemplate="Mês: %{x}<br>Mediana: R$ %{y:,.0f}<extra></extra>",
    ))
    # MoM annotations
    for _, row in df.iterrows():
        if not pd.isna(row["mom_price_pct"]):
            fig_a1.add_annotation(
                x=row["month_pt"],
                y=row["kpi_median_price"],
                text=f"{row['mom_price_pct']:+.1f}%",
                showarrow=False,
                yshift=15,
                font=dict(size=11, color="green" if row["mom_price_pct"] >= 0 else "red"),
            )
    fig_a1.update_layout(
        title="Evolução da Mediana de Preço de Transação — São Paulo (2026)",
        yaxis=dict(title="Mediana (R$)", tickformat="R$ ,.0f"),
        yaxis2=dict(title="Transações", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    st.plotly_chart(fig_a1, use_container_width=True)

    # Chart A2 — Price per m² area fill
    fig_a2 = go.Figure()
    fig_a2.add_trace(go.Scatter(
        x=df["month_pt"],
        y=df["kpi_median_price_per_m2"],
        mode="lines+markers",
        fill="tozeroy",
        name="Mediana Preço/m²",
        line=dict(color="#2ca02c", width=2),
        marker=dict(size=8),
        hovertemplate="Mês: %{x}<br>Mediana/m²: R$ %{y:,.0f}/m²<extra></extra>",
    ))
    for _, row in df.iterrows():
        if not pd.isna(row["mom_m2_pct"]):
            fig_a2.add_annotation(
                x=row["month_pt"],
                y=row["kpi_median_price_per_m2"],
                text=f"{row['mom_m2_pct']:+.1f}%",
                showarrow=False,
                yshift=15,
                font=dict(size=11, color="green" if row["mom_m2_pct"] >= 0 else "red"),
            )
    fig_a2.update_layout(
        title="Evolução da Mediana de Preço por m² — São Paulo (2026)",
        yaxis=dict(title="Mediana/m² (R$)", tickformat="R$ ,.0f"),
        height=400,
    )
    st.plotly_chart(fig_a2, use_container_width=True)


# ---------------------------------------------------------------------------
# Section B — Neighborhood Ranking
# ---------------------------------------------------------------------------

def render_section_b(start_month: str, end_month: str, min_tx_filter: bool):
    st.header("B. Ranking de Bairros")

    min_tx_clause = "AND transaction_count >= 3" if min_tx_filter else ""
    df = query(
        f"""
        SELECT bairro_normalized, month_year, transaction_count,
               kpi_median_price, kpi_median_price_per_m2,
               kpi_mom_price_change_pct, kpi_mom_price_per_m2_change_pct
        FROM gold_itbi_neighborhood_ranking
        WHERE month_year BETWEEN ? AND ?
        {min_tx_clause}
        ORDER BY bairro_normalized, month_year
        """,
        [start_month, end_month],
    )

    if df.empty:
        st.info("Nenhum dado disponível para o período selecionado.")
        return

    df["month_pt"] = df["month_year"].apply(format_month_pt)

    # Chart B1 — Horizontal bar (MoM appreciation)
    available_months = sorted(df["month_year"].unique())
    months_with_mom = df[df["kpi_mom_price_change_pct"].notna()]["month_year"].unique()

    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        selected_month_pt = st.selectbox(
            "Mês do ranking",
            [format_month_pt(m) for m in available_months if m in months_with_mom]
            or [format_month_pt(m) for m in available_months],
            index=len([m for m in available_months if m in months_with_mom]) - 1
            if months_with_mom.any() else 0,
        )
    with col_b2:
        metric_choice = st.radio(
            "Métrica MoM",
            ["Preço", "Preço/m²"],
            horizontal=True,
        )

    top_n = st.number_input("Exibir top N bairros", min_value=5, max_value=100, value=20)

    selected_month = next(
        (m for m in available_months if format_month_pt(m) == selected_month_pt),
        available_months[-1],
    )
    mom_col = "kpi_mom_price_change_pct" if metric_choice == "Preço" else "kpi_mom_price_per_m2_change_pct"

    df_b1 = (
        df[df["month_year"] == selected_month]
        .dropna(subset=[mom_col])
        .nlargest(top_n, mom_col)
    )

    if df_b1.empty:
        st.info("Primeiro mês excluído do ranking (sem base de comparação).")
    else:
        fig_b1 = go.Figure(go.Bar(
            x=df_b1[mom_col],
            y=df_b1["bairro_normalized"],
            orientation="h",
            marker=dict(
                color=df_b1[mom_col],
                colorscale="RdYlGn",
                colorbar=dict(title="%"),
            ),
            hovertemplate=(
                "Bairro: %{y}<br>"
                "Valorização MoM: %{x:.2f}%<br>"
                f"Mediana: R$ " + "%{customdata[0]:,.0f}<br>" +
                "Transações: %{customdata[1]:,}<extra></extra>"
            ),
            customdata=df_b1[["kpi_median_price", "transaction_count"]].values,
        ))
        fig_b1.update_layout(
            title=f"Top {top_n} Bairros por Valorização — {selected_month_pt}",
            xaxis=dict(title="Variação MoM (%)"),
            height=max(400, top_n * 22),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_b1, use_container_width=True)

    # Table B2
    bairro_filter = st.multiselect(
        "Filtrar por bairro",
        sorted(df["bairro_normalized"].unique()),
        default=[],
    )
    df_table = df[df["bairro_normalized"].isin(bairro_filter)] if bairro_filter else df

    display_df = df_table[[
        "bairro_normalized", "month_pt", "transaction_count",
        "kpi_median_price", "kpi_median_price_per_m2",
        "kpi_mom_price_change_pct", "kpi_mom_price_per_m2_change_pct",
    ]].rename(columns={
        "bairro_normalized": "Bairro",
        "month_pt": "Mês",
        "transaction_count": "Transações",
        "kpi_median_price": "Mediana Preço (R$)",
        "kpi_median_price_per_m2": "Mediana Preço/m² (R$)",
        "kpi_mom_price_change_pct": "Variação MoM Preço (%)",
        "kpi_mom_price_per_m2_change_pct": "Variação MoM /m² (%)",
    })

    def color_mom(val):
        if pd.isna(val):
            return "color: grey; font-style: italic"
        return "color: green; font-weight: bold" if val >= 0 else "color: red; font-weight: bold"

    styled = (
        display_df.style
        .applymap(color_mom, subset=["Variação MoM Preço (%)", "Variação MoM /m² (%)"])
        .format({
            "Mediana Preço (R$)": lambda x: format_brl(x),
            "Mediana Preço/m² (R$)": lambda x: f"{format_brl(x)}/m²" if x == x else "—",
            "Variação MoM Preço (%)": lambda x: format_pct(x),
            "Variação MoM /m² (%)": lambda x: format_pct(x),
            "Transações": lambda x: f"{int(x):,}",
        })
    )
    st.dataframe(styled, use_container_width=True, height=400)


# ---------------------------------------------------------------------------
# Section C — Price per m² Drill-down
# ---------------------------------------------------------------------------

def render_section_c(start_month: str, end_month: str, min_tx_filter: bool):
    st.header("C. Drill-down Preço/m²")

    min_tx_clause = "AND transaction_count >= 3" if min_tx_filter else ""
    df = query(
        f"""
        SELECT bairro_normalized, uso_desc, month_year,
               transaction_count, kpi_median_price_per_m2, kpi_avg_price_per_m2
        FROM gold_itbi_price_per_m2
        WHERE month_year BETWEEN ? AND ?
        {min_tx_clause}
        ORDER BY bairro_normalized, uso_desc, month_year
        """,
        [start_month, end_month],
    )

    if df.empty:
        st.info("Nenhum dado disponível para o período selecionado.")
        return

    df["month_pt"] = df["month_year"].apply(format_month_pt)
    df["uso_display"] = df["uso_desc"].apply(lambda x: "Tipo não identificado" if x == "UNKNOWN" else x)

    all_bairros = sorted(df["bairro_normalized"].unique())
    all_usos = sorted(df["uso_display"].unique())

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        selected_bairros = st.multiselect(
            "Selecionar bairros para análise",
            all_bairros,
            default=[],
            max_selections=10,
        )
    with col_c2:
        selected_usos = st.multiselect(
            "Tipo de uso",
            all_usos,
            default=[],
        )

    # Default: top 3 bairros by transaction volume
    if not selected_bairros:
        top3 = (
            df.groupby("bairro_normalized")["transaction_count"]
            .sum()
            .nlargest(3)
            .index.tolist()
        )
        selected_bairros = top3
        st.info(f"Exibindo top 3 bairros por volume: {', '.join(top3)}")

    df_c = df[df["bairro_normalized"].isin(selected_bairros)]
    if selected_usos:
        df_c = df_c[df_c["uso_display"].isin(selected_usos)]

    if len(selected_bairros) > 5:
        st.warning("Mais de 5 bairros selecionados — considere reduzir para melhor legibilidade.")

    # Chart C1 — Multi-series line
    fig_c1 = go.Figure()
    colors = px.colors.qualitative.Set1
    linestyles = ["solid", "dash", "dot", "dashdot"]

    combos = df_c.groupby(["bairro_normalized", "uso_display"])
    for i, ((bairro, uso), grp) in enumerate(combos):
        grp = grp.sort_values("month_year")
        fig_c1.add_trace(go.Scatter(
            x=grp["month_pt"],
            y=grp["kpi_median_price_per_m2"],
            mode="lines+markers",
            name=f"{bairro} — {uso}",
            line=dict(
                color=colors[i % len(colors)],
                dash=linestyles[(i // len(colors)) % len(linestyles)],
                width=2,
            ),
            connectgaps=False,
            hovertemplate=(
                f"Bairro: {bairro}<br>"
                f"Tipo: {uso}<br>"
                "Mês: %{x}<br>"
                "Mediana/m²: R$ %{y:,.0f}/m²<br>"
                "Transações: %{customdata:,}<extra></extra>"
            ),
            customdata=grp["transaction_count"].values,
        ))

    fig_c1.update_layout(
        title="Preço por m² por Bairro e Tipo de Uso",
        yaxis=dict(title="Mediana/m² (R$)"),
        height=450,
        legend=dict(orientation="h", yanchor="top", y=-0.2),
    )
    if df_c["kpi_median_price_per_m2"].isna().any():
        st.caption("Lacunas indicam meses sem transações com área construída informada.")
    st.plotly_chart(fig_c1, use_container_width=True)

    # Chart C2 — Bar by uso_desc, latest month
    latest_month = df_c["month_year"].max()
    latest_month_pt = format_month_pt(latest_month)
    df_c2 = df_c[df_c["month_year"] == latest_month]

    if not df_c2.empty:
        fig_c2 = go.Figure()
        for bairro in selected_bairros:
            grp = df_c2[df_c2["bairro_normalized"] == bairro]
            if grp.empty:
                continue
            fig_c2.add_trace(go.Bar(
                name=bairro,
                x=grp["uso_display"],
                y=grp["kpi_median_price_per_m2"],
                hovertemplate="Tipo: %{x}<br>Mediana/m²: R$ %{y:,.0f}/m²<extra></extra>",
            ))
            fig_c2.add_trace(go.Scatter(
                name=f"{bairro} (média)",
                x=grp["uso_display"],
                y=grp["kpi_avg_price_per_m2"],
                mode="markers",
                marker=dict(size=10, symbol="diamond"),
                showlegend=False,
                hovertemplate="Tipo: %{x}<br>Média/m²: R$ %{y:,.0f}/m²<extra></extra>",
            ))

        fig_c2.update_layout(
            title=f"Preço Mediano por m² por Tipo de Uso — {latest_month_pt}",
            barmode="group",
            yaxis=dict(title="R$/m²"),
            height=400,
        )
        st.plotly_chart(fig_c2, use_container_width=True)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main():
    st.title("Dashboard ITBI São Paulo — 2026")
    st.caption("Dados: Prefeitura de SP · Valores declarados pelo contribuinte · Uso exclusivo para análise")

    start_month, end_month, min_tx_filter = render_sidebar()

    if start_month is None:
        st.warning("Nenhum dado encontrado. Execute `make pipeline` primeiro.")
        return

    render_section_a(start_month, end_month)
    st.divider()
    render_section_b(start_month, end_month, min_tx_filter)
    st.divider()
    render_section_c(start_month, end_month, min_tx_filter)


if __name__ == "__main__":
    main()
