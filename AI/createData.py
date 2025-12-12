import pandas as pd
import time
import os
import random

# Import des classes depuis ton fichier principal
from mainGame import (
    play_public_goods_game,
    GAME_CONFIG,
    LLMStrategy,
    Altruist,
    FreeRider,
    ConditionalCooperator,
)

# --- CONFIGURATION DE LA GÉNÉRATION ---

# Choisis ton modèle ici (assure-toi qu'il est "pull" dans Ollama)
MODEL_NAME = "gemma2"  # ou "mistral", "llama3", etc.

# On réduit les tours pour l'IA (trop long sinon)
AI_GAME_CONFIG = {
    "endowment": 20,
    "multiplier": 1.6,
    "n_rounds": 200,  # 200 tours suffisent pour voir une dynamique
}

# Nombre de répétitions par scénario
N_GAMES_PER_SCENARIO = 1


def run_ai_simulation(players):
    all_records = []
    game_counter = 0

    print(f"🚀 Démarrage de la simulation IA avec le modèle : {MODEL_NAME}")
    print(
        f"⚙️ Config : {AI_GAME_CONFIG['n_rounds']} tours | {N_GAMES_PER_SCENARIO} parties par scénario"
    )

    for i in range(N_GAMES_PER_SCENARIO):
        game_counter += 1
        print(f"   > Partie {i+1}/{N_GAMES_PER_SCENARIO}...", end=" ", flush=True)

        # Mélanger l'ordre des joueurs autour de la table
        random.shuffle(players)

        data = play_public_goods_game(players, AI_GAME_CONFIG)

        # Ajout métadonnées
        for row in data:
            row["game_id"] = f"IA_S1_{int(time.time())}_{game_counter}"
            row["scenario"] = "Full_IA_Psychology"
            row["model_used"] = MODEL_NAME
            all_records.append(row)
        print("✅ Terminée.")

    return pd.DataFrame(all_records)


def save_ia_data(df, folder="data", filename="simulation_ia_results.parquet"):
    if not os.path.exists(folder):
        os.makedirs(folder)

    filepath = os.path.join(folder, filename)
    df.to_parquet(filepath, index=False)
    print(f"\n🎉 Sauvegarde terminée : {filepath}")
    print(f"📊 Total : {len(df)} lignes générées.")


if __name__ == "__main__":
    # 1. Générer
    try:
        # players = [
        #     LLMStrategy(model_name=MODEL_NAME, persona="greedy"),
        #     LLMStrategy(model_name=MODEL_NAME, persona="altruist"),
        #     LLMStrategy(model_name=MODEL_NAME, persona="adaptive"),
        #     LLMStrategy(
        #         model_name=MODEL_NAME, persona="adaptive"
        #     ),  # Un 2ème adaptatif pour faire la majorité
        # ]
        # filename = "simulation_ia_results1.parquet"

        # players = [
        #     LLMStrategy(model_name=MODEL_NAME, persona="adaptive"),  # Notre cobaye
        #     ConditionalCooperator(),  # Le suiveur (code)
        #     FreeRider(),  # Le méchant (code)
        #     Altruist(),  # Le gentil (code)
        # ]
        # filename = "simulation_ia_results2.parquet"

        players = [
            LLMStrategy(model_name=MODEL_NAME, persona="altruist"),
            LLMStrategy(model_name=MODEL_NAME, persona="greedy"),
            LLMStrategy(model_name=MODEL_NAME, persona="greedy"),
            LLMStrategy(model_name=MODEL_NAME, persona="greedy"),
        ]
        filename = "simulation_ia_results3.parquet"

        df_ia = run_ai_simulation(players)

        # 2. Sauvegarder
        # On sauvegarde dans un fichier DIFFÉRENT de la simulation pure code
        # pour ne pas écraser tes précédentes données.
        save_ia_data(df_ia, filename=filename)

    except KeyboardInterrupt:
        print("\n🛑 Interruption par l'utilisateur. Sauvegarde partielle...")
        # Si tu coupes le script parce que c'est trop long, ça plantera pas tout
