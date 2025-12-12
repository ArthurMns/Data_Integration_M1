import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Public Goods Analysis", layout="wide")

st.title("📊 Analyse du Jeu du Bien Public")
st.markdown("Exploration des résultats de simulation via **DuckDB** et **Streamlit**.")

# --- CHARGEMENT DES DONNÉES VIA DUCKDB ---


# On utilise une fonction avec @st.cache_data pour ne pas re-exécuter la requête à chaque clic
@st.cache_data
def load_summary_stats():
    query = """
    SELECT 
        COUNT(DISTINCT game_id) as total_games,
        AVG(group_synergy_factor) as avg_multiplier,
        AVG(contribution) as avg_contribution,
        AVG(round_gain_total) as avg_gain
    FROM 'simulation_results.parquet'
    """
    return duckdb.sql(query).df()


@st.cache_data
def load_strategy_performance():
    query = """
    SELECT 
        strategy, 
        AVG(contribution) as mean_contribution,
        AVG(cumulative_score) as mean_final_score,
        COUNT(*) as count_decisions
    FROM 'simulation_results.parquet'
    -- On prend le score cumulé seulement au dernier tour pour avoir le total
    WHERE round = 50 
    GROUP BY strategy
    ORDER BY mean_final_score DESC
    """
    return duckdb.sql(query).df()


@st.cache_data
def load_evolution_over_time():
    query = """
    SELECT 
        round,
        strategy,
        AVG(contribution) as avg_contribution
    FROM 'simulation_results.parquet'
    GROUP BY round, strategy
    ORDER BY round
    """
    return duckdb.sql(query).df()


# --- INTERFACE UTILISATEUR ---

# 1. KPIs en haut de page
stats = load_summary_stats()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Parties jouées", f"{stats['total_games'][0]:.0f}")
col2.metric("Multiplicateur Moyen", f"x{stats['avg_multiplier'][0]:.2f}")
col3.metric("Mise Moyenne", f"{stats['avg_contribution'][0]:.1f}")
col4.metric("Gain Moyen / Tour", f"{stats['avg_gain'][0]:.1f}")

st.divider()

# 2. Analyse des Stratégies (Qui gagne ?)
st.subheader("🏆 Performance des Stratégies")
col_chart1, col_chart2 = st.columns(2)

df_perf = load_strategy_performance()

with col_chart1:
    st.markdown("**Qui gagne le plus de points ?**")
    fig_score = px.bar(
        df_perf,
        x="strategy",
        y="mean_final_score",
        color="strategy",
        title="Score Final Moyen par Stratégie",
        text_auto=".0f",
    )
    st.plotly_chart(fig_score, use_container_width=True)

with col_chart2:
    st.markdown("**Qui contribue le plus au pot commun ?**")
    fig_contrib = px.bar(
        df_perf,
        x="strategy",
        y="mean_contribution",
        color="strategy",
        title="Contribution Moyenne par Stratégie",
        text_auto=".1f",
    )
    st.plotly_chart(fig_contrib, use_container_width=True)

# 3. Évolution Temporelle (La chute de la coopération ?)
st.subheader("📉 Évolution de la Coopération au fil des tours")
df_time = load_evolution_over_time()

fig_line = px.line(
    df_time,
    x="round",
    y="avg_contribution",
    color="strategy",
    title="Mise moyenne par tour (Dynamique temporelle)",
    markers=True,
)
st.plotly_chart(fig_line, use_container_width=True)

# 4. Requêteur SQL Libre (Pour le Data Analyst)
st.divider()
st.subheader("🕵️ Requêteur SQL DuckDB")
sql_query = st.text_area(
    "Écrivez votre requête SQL ici (table : 'simulation_results.parquet')",
    "SELECT * FROM 'simulation_results.parquet' LIMIT 10",
)

if sql_query:
    try:
        # Exécution directe via DuckDB
        result_df = duckdb.sql(sql_query).df()
        st.dataframe(result_df)
    except Exception as e:
        st.error(f"Erreur SQL : {e}")
