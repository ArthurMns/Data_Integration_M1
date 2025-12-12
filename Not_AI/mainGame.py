import random
from abc import ABC, abstractmethod
import pandas as pd  # Optionnel ici, mais utile pour visualiser à la fin

# --- CONFIGURATION DU JEU ---

GAME_CONFIG = {
    "endowment": 20,  # Dotation initiale par tour
    "multiplier": 2,  # Facteur multiplicateur du pot commun (Synergie)
    "n_rounds": 200,  # Nombre de tours
}

# Note sur le Multiplicateur :
# Si Multiplicateur < 1 : Personne ne doit jouer (perte sèche).
# Si Multiplicateur > N_joueurs : Tout le monde gagne à jouer (pas de dilemme).
# Le dilemme existe si : 1 < Multiplicateur < N_joueurs.

# --- DÉFINITION DES STRATÉGIES ---


class Strategy(ABC):
    @abstractmethod
    def decide_contribution(self, history_global, my_id, endowment):
        """
        :param history_global: Liste de dicts contenant les tours précédents
                               (ex: [{'contributions': {0: 10, 1: 0}, 'pot': 20}, ...])
        :param my_id: Identifiant unique du joueur (int)
        :param endowment: La somme disponible ce tour-ci
        :return: int (montant de la contribution)
        """
        pass

    def get_name(self):
        return self.__class__.__name__


class Altruist(Strategy):
    """Met tout dans le pot commun."""

    def decide_contribution(self, history_global, my_id, endowment):
        return endowment


class FreeRider(Strategy):
    """Le Passager Clandestin : garde tout, ne met rien."""

    def decide_contribution(self, history_global, my_id, endowment):
        return 0


class RandomPlayer(Strategy):
    """Joue au hasard."""

    def decide_contribution(self, history_global, my_id, endowment):
        return random.randint(0, endowment)


class ConditionalCooperator(Strategy):
    """
    Suit le groupe : met la moyenne de ce que les autres ont mis au tour précédent.
    Au premier tour, il est prudent (met 50%).
    """

    def decide_contribution(self, history_global, my_id, endowment):
        if not history_global:
            return endowment // 2

        # Récupérer les contributions du tour précédent
        last_round = history_global[-1]["contributions"]

        # Calculer la moyenne des mises (sauf la mienne, pour voir l'ambiance des autres)
        others_contributions = [amt for pid, amt in last_round.items() if pid != my_id]

        if not others_contributions:  # Cas s'il joue seul (peu probable)
            return 0

        avg_others = sum(others_contributions) / len(others_contributions)
        return int(avg_others)


# --- MOTEUR DE SIMULATION (PIPELINE DATA) ---


def play_public_goods_game(players_strategies, config):
    """
    Joue une partie complète à N joueurs.
    :param players_strategies: Liste d'instances de stratégies [s1, s2, s3...]
    :param config: Dictionnaire de configuration
    :return: Liste de dictionnaires (Flat Data pour ETL)
    """
    history_global = []  # État du jeu tour par tour pour la prise de décision
    dataset = []  # Données aplaties pour l'export

    n_players = len(players_strategies)
    # Initialisation des scores cumulés pour le suivi
    cumulative_scores = {i: 0 for i in range(n_players)}

    print(
        f"--- DÉBUT DU JEU : {n_players} Joueurs, Multiplicateur x{config['multiplier']} ---"
    )

    for round_num in range(1, config["n_rounds"] + 1):

        current_contributions = {}

        # 1. Phase de Décision (COLLECT)
        for pid, strategy in enumerate(players_strategies):
            contribution = strategy.decide_contribution(
                history_global, pid, config["endowment"]
            )
            # Sécurité : on borne la contribution entre 0 et endowment
            contribution = max(0, min(contribution, config["endowment"]))
            current_contributions[pid] = contribution

        # 2. Calcul du Pot et Redistribution (TRANSFORM)
        total_pot = sum(current_contributions.values())
        multiplied_pot = total_pot * config["multiplier"]
        share_per_player = multiplied_pot / n_players

        # Enregistrement pour l'historique de jeu (utile aux stratégies)
        history_global.append(
            {
                "round": round_num,
                "contributions": current_contributions,
                "total_pot": total_pot,
            }
        )

        # 3. Calcul des gains et génération des données (LOAD PREP)
        for pid, strategy in enumerate(players_strategies):
            # Formule : Ce que j'ai gardé + Ma part du pot commun
            kept = config["endowment"] - current_contributions[pid]
            round_gain = kept + share_per_player

            cumulative_scores[pid] += round_gain

            # Création de la ligne de donnée "Tidy"
            # Chaque ligne représente l'action d'UN joueur à UN tour
            record = {
                "round": round_num,
                "player_id": pid,
                "strategy": strategy.get_name(),
                "endowment": config["endowment"],
                "contribution": current_contributions[pid],
                "kept_private": kept,
                "pot_share_received": round_gain - kept,  # La part reçue du pot
                "round_gain_total": round_gain,
                "cumulative_score": cumulative_scores[pid],
                "group_total_pot": total_pot,
                "group_synergy_factor": config["multiplier"],
            }
            dataset.append(record)

    return dataset


# --- EXEMPLE D'EXÉCUTION ---

if __name__ == "__main__":
    # Créons une table de 5 joueurs avec des profils mixtes
    table_of_players = [
        Altruist(),  # Le bon samaritain
        FreeRider(),  # Le profiteur
        ConditionalCooperator(),  # Le suiveur (x2)
        RandomPlayer(),  # L'élément chaotique
    ]

    # Lancement de la simulation
    raw_data = play_public_goods_game(table_of_players, GAME_CONFIG)

    # Aperçu des données (5 dernières lignes)
    print(f"\nDonnées générées : {len(raw_data)} lignes.")
    print("Exemple des dernières actions :")
    for row in raw_data[-5:]:
        # Affichage simplifié
        print(
            f"Tour {row['round']} | J{row['player_id']} ({row['strategy']}) : "
            f"A mis {row['contribution']} | Gain {row['round_gain_total']:.2f}"
        )

    # Pour voir qui a gagné :
    # (Si tu as pandas installé, sinon tu peux ignorer)
    try:
        df = pd.DataFrame(raw_data)
        final_scores = df[df["round"] == GAME_CONFIG["n_rounds"]].sort_values(
            "cumulative_score", ascending=False
        )
        print("\n--- CLASSEMENT FINAL ---")
        print(final_scores[["strategy", "cumulative_score"]])
    except ImportError:
        pass
