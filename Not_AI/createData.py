import os
import pandas as pd
import random
import time
from mainGame import (
    play_public_goods_game,
    Altruist,
    FreeRider,
    RandomPlayer,
    ConditionalCooperator,
)

# ... (Assure-toi d'avoir les classes Strategy, Altruist, FreeRider, etc. définies au-dessus) ...


def run_simulation_batch(n_games=50):
    """
    Lance une série de simulations avec des compositions aléatoires
    et retourne un DataFrame global.
    """
    all_records = []

    # Définition de stratégies possibles pour composer les tables
    available_strategies = [Altruist, FreeRider, RandomPlayer, ConditionalCooperator]

    print(f"🚀 Lancement de {n_games} parties simulées...")

    for game_id in range(1, n_games + 1):
        # 1. Composition aléatoire de la table (entre 3 et 6 joueurs)
        n_players = random.randint(3, 6)
        strategies = []
        for _ in range(n_players):
            # On instancie une stratégie au hasard
            strat_class = random.choice(available_strategies)
            strategies.append(strat_class())

        # 2. Configuration (on peut faire varier le multiplicateur pour analyser son impact plus tard !)
        # Par exemple : un multiplicateur aléatoire entre 1.2 et 2.5
        config = {
            "endowment": 20,
            "multiplier": round(random.uniform(1.2, 2.5), 2),
            "n_rounds": 50,
        }

        # 3. Lancement du jeu
        # (On suppose que la fonction play_public_goods_game est définie comme avant)
        game_data = play_public_goods_game(strategies, config)

        # 4. Enrichissement des données avec l'ID de la partie
        for row in game_data:
            row["game_id"] = f"game_{int(time.time())}_{game_id}"  # ID unique
            row["n_players"] = n_players  # Utile pour l'analyse
            all_records.append(row)

    # 5. Conversion en DataFrame Pandas
    df = pd.DataFrame(all_records)
    return df


def save_to_parquet(df, filename="./simulation_results.parquet"):
    """
    Sauvegarde le DataFrame en fichier Parquet.
    """

    # Sauvegarde en Parquet (nécessite pyarrow ou fastparquet installé)
    # index=False car l'index pandas n'est pas utile ici
    df.to_parquet(filename, index=False)

    print(f"✅ Données sauvegardées avec succès : {filename}")
    print(f"📊 Dimensions : {df.shape[0]} lignes x {df.shape[1]} colonnes")


# --- EXÉCUTION ---

if __name__ == "__main__":
    # 1. Générer les données (Batch de 200 parties)
    df_results = run_simulation_batch(n_games=200)

    # 2. Sauvegarder
    save_to_parquet(df_results)

    # 3. Petit aperçu pour vérifier
    print("\n--- Aperçu des données ---")
    print(df_results.head())
