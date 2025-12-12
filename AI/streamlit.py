import streamlit as st
import duckdb
import plotly.express as px
import os
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="IA & Théorie des Jeux", page_icon="🤖", layout="wide")

st.title("🤖 Analyse des Stratégies IA (Public Goods Game)")
st.markdown(
    """
Visualisation des expériences comportementales : **Greedy** (Avare), **Altruist** (Bienveillant) et **Adaptive** (Adaptatif).
"""
)

# --- CONFIGURATION DES FICHIERS ---
SCENARIOS = {
    "Scénario 1 : Le Choc des Psychologies (Full IA)": "data/simulation_IA_results1.parquet",
    "Scénario 2 : L'IA face aux Robots (IA vs Code)": "data/simulation_IA_results2.parquet",
    "Scénario 3 : Le Cauchemar (1 Altruiste vs 3 Greedy)": "data/simulation_IA_results3.parquet",
}

# --- BARRE LATÉRALE ---
st.sidebar.header("📁 Choix de l'Expérience")
selected_scenario_name = st.sidebar.radio(
    "Sélectionnez le scénario :", list(SCENARIOS.keys())
)
current_file = SCENARIOS[selected_scenario_name]

if not os.path.exists(current_file):
    st.error(f"⚠️ Fichier introuvable : {current_file}")
    st.stop()

# --- FONCTIONS DUCKDB ---


@st.cache_data
def get_kpis(filename):
    query = f"""
    SELECT 
        COUNT(DISTINCT game_id) as nb_parties,
        AVG(contribution) as mise_moyenne,
        AVG(round_gain_total) as gain_moyen,
        MAX(model_used) as modele_ia
    FROM '{filename}'
    """
    return duckdb.sql(query).df()


@st.cache_data
def get_timeline_aggregated(filename):
    """Moyenne globale par stratégie (Vue d'ensemble)"""
    query = f"""
    SELECT 
        round,
        strategy,
        AVG(contribution) as contribution_moyenne
    FROM '{filename}'
    GROUP BY round, strategy
    ORDER BY round
    """
    return duckdb.sql(query).df()


def get_list_of_games(filename):
    """Récupère la liste des IDs de parties disponibles"""
    query = f"SELECT DISTINCT game_id FROM '{filename}'"
    return duckdb.sql(query).df()["game_id"].tolist()


def get_single_game_data(filename, game_id):
    """Récupère les données d'une seule partie pour voir les joueurs individuels"""
    query = f"""
    SELECT 
        round,
        player_id,
        strategy,
        contribution,
        cumulative_score
    FROM '{filename}'
    WHERE game_id = '{game_id}'
    ORDER BY round, player_id
    """
    df = duckdb.sql(query).df()
    # On crée une étiquette unique pour distinguer les joueurs ayant la même stratégie
    # Ex: "J0 (Greedy)", "J1 (Greedy)"
    df["player_label"] = "J" + df["player_id"].astype(str) + " (" + df["strategy"] + ")"
    return df


@st.cache_data
def get_ranking_data(filename):
    query = f"""
    SELECT 
        strategy,
        AVG(contribution) as contribution_globale,
        AVG(cumulative_score) as score_final
    FROM '{filename}'
    WHERE round = (SELECT MAX(round) FROM '{filename}')
    GROUP BY strategy
    ORDER BY score_final DESC
    """
    return duckdb.sql(query).df()


def get_single_game_ranking(filename, game_id):
    """Récupère le classement final pour UNE partie spécifique avec ID joueurs"""
    # On récupère le score cumulé au dernier tour pour chaque joueur
    query = f"""
    SELECT 
        player_id,
        strategy,
        MAX(cumulative_score) as score_final,
        AVG(contribution) as contribution_moyenne_partie
    FROM '{filename}'
    WHERE game_id = '{game_id}'
    GROUP BY player_id, strategy
    ORDER BY score_final DESC
    """
    df = duckdb.sql(query).df()
    # Création de l'étiquette unique
    df["player_label"] = "J" + df["player_id"].astype(str) + " (" + df["strategy"] + ")"
    return df


# --- INTERFACE ---

# CHARGEMENT KPIS
kpis = get_kpis(current_file)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Modèle", kpis["modele_ia"][0])
col2.metric("Mise Moyenne", f"{kpis['mise_moyenne'][0]:.1f}")
col3.metric("Gain Moyen", f"{kpis['gain_moyen'][0]:.1f}")
col4.metric("Nb Parties", f"{kpis['nb_parties'][0]}")

st.divider()

# ONGLETS
tab1, tab2, tab3 = st.tabs(
    ["📉 Dynamique (Temps)", "🏆 Classement", "🔍 Données Brutes"]
)

with tab1:
    # --- PARTIE 1 : VUE GLOBALE (MOYENNE) ---
    st.subheader("1. Tendance Globale (Moyenne des stratégies)")
    df_agg = get_timeline_aggregated(current_file)
    fig_agg = px.line(
        df_agg,
        x="round",
        y="contribution_moyenne",
        color="strategy",
        markers=True,
        title="Moyenne de tous les joueurs confondus",
        range_y=[-1, 21],
    )
    st.plotly_chart(fig_agg, use_container_width=True)

    st.divider()

    # --- PARTIE 2 : ZOOM SUR UNE PARTIE ---
    st.subheader("2. 🔬 Zoom sur une partie spécifique (Détail Joueurs)")
    st.info(
        "Ici, chaque courbe représente un joueur unique. C'est idéal pour voir le Scénario 3."
    )

    # Sélecteur de partie
    game_ids = get_list_of_games(current_file)
    selected_game_id = st.selectbox("Choisir une partie à analyser :", game_ids)

    if selected_game_id:
        df_single = get_single_game_data(current_file, selected_game_id)

        # Graphique
        fig_single = px.line(
            df_single,
            x="round",
            y="contribution",
            color="player_label",  # C'est ici que la magie opère (J0, J1, etc.)
            markers=True,
            symbol="player_label",
            title=f"Mises tour par tour (Partie : {selected_game_id})",
            range_y=[-1, 21],
        )
        # Ajout d'une zone rouge pour la trahison (0-5) et verte pour coop (15-20)
        fig_single.add_shape(
            type="rect",
            x0=0,
            y0=0,
            x1=15,
            y1=5,
            fillcolor="red",
            opacity=0.1,
            line_width=0,
        )

        st.plotly_chart(fig_single, use_container_width=True)

        # Petit tableau des scores de cette partie
        st.caption("Scores finaux de cette partie spécifique :")
        final_scores = df_single[df_single["round"] == df_single["round"].max()][
            ["player_label", "cumulative_score"]
        ].sort_values("cumulative_score", ascending=False)
        st.dataframe(final_scores, hide_index=True)

with tab2:
    st.subheader("🏆 Classement et Performance")

    # Choix du mode de vue
    view_mode = st.radio(
        "Mode d'affichage :",
        ["Vue Détaillée (Une partie)", "Vue Globale (Moyenne de toutes les parties)"],
        horizontal=True,
    )

    if view_mode == "Vue Détaillée (Une partie)":
        # On réutilise la liste des games
        game_ids = get_list_of_games(current_file)
        # On essaie de garder la même sélection que dans l'onglet 1 si possible, sinon le premier
        selected_game_rank = st.selectbox(
            "Choisir la partie à classer :", game_ids, key="rank_select"
        )

        if selected_game_rank:
            df_rank_single = get_single_game_ranking(current_file, selected_game_rank)

            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.markdown(f"**💰 Score Final (Partie {selected_game_rank})**")
                fig_score_s = px.bar(
                    df_rank_single,
                    x="player_label",  # AXE X unique (J0, J1...)
                    y="score_final",
                    color="strategy",  # On garde la couleur par stratégie
                    text_auto=".0f",
                    title="Qui a gagné cette partie ?",
                )
                st.plotly_chart(fig_score_s, use_container_width=True)

            with col_r2:
                st.markdown("**❤️ Générosité Moyenne sur la partie**")
                fig_contrib_s = px.bar(
                    df_rank_single,
                    x="player_label",
                    y="contribution_moyenne_partie",
                    color="strategy",
                    text_auto=".1f",
                    title="Qui a le plus contribué ?",
                )
                st.plotly_chart(fig_contrib_s, use_container_width=True)

    else:
        # VUE GLOBALE (L'ancienne vue)
        st.info(
            "Cette vue affiche la moyenne de TOUTES les parties simulées. Les joueurs de même type sont regroupés."
        )
        df_rank_global = get_ranking_data(current_file)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_score = px.bar(
                df_rank_global,
                x="strategy",
                y="score_final",
                color="strategy",
                title="Score Final Moyen (Global)",
                text_auto=".0f",
            )
            st.plotly_chart(fig_score, use_container_width=True)
        with col_g2:
            fig_contrib = px.bar(
                df_rank_global,
                x="strategy",
                y="contribution_globale",
                color="strategy",
                title="Contribution Moyenne (Globale)",
                text_auto=".1f",
            )
            st.plotly_chart(fig_contrib, use_container_width=True)

with tab3:
    st.subheader("Données Brutes")
    st.dataframe(duckdb.sql(f"SELECT * FROM '{current_file}' LIMIT 100").df())
