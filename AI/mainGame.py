import random
import re
from abc import ABC, abstractmethod
import pandas as pd

# On tente d'importer ollama, si ça échoue on prévient l'utilisateur
try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print(
        "⚠️ Attention : la librairie 'ollama' n'est pas installée. Les stratégies IA ne fonctionneront pas."
    )

# --- CONFIGURATION DU JEU ---

PERSONA_PROMPTS = {
    "altruist": """
    Tu es un **Coopérateur Bienveillant**.
    Ta philosophie : La réussite du groupe est plus importante que ta réussite individuelle.
    Stratégie :
    - Tu mises généralement des montants élevés (entre 15 et 20) pour donner l'exemple.
    - Si les autres trahissent (mises faibles), ne te venge pas immédiatement. Continue de miser haut encore un ou deux tours pour voir s'ils changent.
    - Seulement si l'abus est flagrant et répété, réduis ta mise pour te protéger, mais reste toujours au-dessus de la moyenne.
    Ton but est d'inspirer la confiance.
    """,
    "greedy": """
    Tu es un **Calculateur Opportuniste**.
    Ta philosophie : Les autres sont là pour enrichir le pot, toi tu es là pour l'encaisser.
    Stratégie :
    - Ton but est d'avoir un score individuel plus haut que les autres à la fin.
    - Ne mets pas 0 systématiquement, car les autres vont arrêter de jouer (et le pot sera vide).
    - Essaie de mettre un peu MOINS que la moyenne observée (par exemple, s'ils mettent 15, mets 8 ou 10).
    - Fais croire que tu coopères, mais garde toujours une marge de profit pour toi.
    """,
    "adaptive": """
    Tu es un **Joueur Pragmatique et Équitable**.
    Ta philosophie : Donnant-donnant. Je ne veux pas être le dindon de la farce, ni le méchant.
    Stratégie :
    - Analyse l'historique : combien ont mis les autres au tour précédent ?
    - Mises à peu près la même chose que la moyenne des autres.
    - Si la confiance règne, augmente tes mises vers le maximum.
    - Si tu sens que ça trahit (mises basses), baisse immédiatement ta mise au tour suivant pour ne pas perdre d'argent.
    Sois juste : ni naïf, ni voleur.
    """,
}

GAME_CONFIG = {
    "endowment": 20,
    "multiplier": 1.6,
    "n_rounds": 20,  # On réduit un peu les tours car l'IA est plus lente que le code pur
}

# --- DÉFINITION DES STRATÉGIES ---


class Strategy(ABC):
    @abstractmethod
    def decide_contribution(self, history_global, my_id, endowment):
        pass

    def get_name(self):
        return self.__class__.__name__


# ... (Garder ici les classes classiques : Altruist, FreeRider, ConditionalCooperator, RandomPlayer) ...
# Je les remets brièvement pour que le code soit autonome :


class Altruist(Strategy):
    def decide_contribution(self, history_global, my_id, endowment):
        return endowment


class FreeRider(Strategy):
    def decide_contribution(self, history_global, my_id, endowment):
        return 0


class RandomPlayer(Strategy):
    def decide_contribution(self, history_global, my_id, endowment):
        return random.randint(0, endowment)


class ConditionalCooperator(Strategy):
    def decide_contribution(self, history_global, my_id, endowment):
        if not history_global:
            return endowment // 2
        last_round = history_global[-1]["contributions"]
        others = [amt for pid, amt in last_round.items() if pid != my_id]
        if not others:
            return 0
        return int(sum(others) / len(others))


# --- NOUVELLE STRATÉGIE : AGENT LLM ---


class LLMStrategy(Strategy):
    def __init__(self, model_name="llama3", persona="adaptive", stream=False):
        self.model_name = model_name
        self.persona = persona  # doit être 'altruist', 'greedy', ou 'adaptive'
        self.stream = stream

    def get_name(self):
        return f"IA_{self.persona}_{self.model_name}"

    def _build_prompt(self, history_global, my_id, endowment):
        # 1. Récupération de l'instruction de personnalité
        # Si le persona n'existe pas, on prend 'adaptive' par défaut
        persona_instruction = PERSONA_PROMPTS.get(
            self.persona, PERSONA_PROMPTS["adaptive"]
        )

        # 2. Construction de l'historique (Context)
        history_text = ""
        if not history_global:
            history_text = "C'est le tout premier tour. Tu ne connais pas encore les autres joueurs."
        else:
            recent_history = history_global[
                -3:
            ]  # On regarde seulement les 3 derniers tours
            history_text = "### Historique récent du jeu :\n"
            for h in recent_history:
                # Analyse précise pour l'IA
                others_contrib = [
                    v for k, v in h["contributions"].items() if k != my_id
                ]
                avg_others = (
                    sum(others_contrib) / len(others_contrib) if others_contrib else 0
                )
                my_last = h["contributions"][my_id]

                history_text += (
                    f"- Tour {h['round']} : J'ai mis {my_last}/{endowment}. "
                    f"Les autres ont mis en moyenne {avg_others:.1f}/{endowment}. "
                    f"Pot total généré : {h['total_pot']}.\n"
                )

        # 3. Prompt Final
        prompt = f"""
        CONTEXTE :
        Tu participes à une simulation du "Jeu du Bien Public" contre d'autres joueurs.
        
        RÈGLES MATHÉMATIQUES :
        - Dotation par tour : {endowment} jetons.
        - Ta mise : entre 0 et {endowment}.
        - Le pot commun est multiplié par {GAME_CONFIG['multiplier']} (synergie) puis partagé équitablement entre tous.
        - Ton gain = (Ce que tu gardes) + (Ta part du pot).
        
        TON RÔLE :
        {persona_instruction}
        
        SITUATION ACTUELLE :
        {history_text}
        
        TA DÉCISION :
        Combien mises-tu pour ce tour-ci ?
        Analyse la situation selon ton rôle, puis donne ta réponse.
        
        FORMAT DE RÉPONSE ATTENDU :
        Réponds UNIQUEMENT par un nombre entier (rien d'autre, pas de texte).
        Exemple : 12
        """
        return prompt

    # ... (le reste de la classe : decide_contribution, init, etc. reste identique)

    def decide_contribution(self, history_global, my_id, endowment):
        if not OLLAMA_AVAILABLE:
            return 0  # Fallback si pas de librairie

        prompt = self._build_prompt(history_global, my_id, endowment)

        try:
            # Appel à l'API Ollama
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            content = response["message"]["content"]

            # Nettoyage de la réponse (Extraction du premier nombre trouvé)
            # Les LLM ajoutent souvent du texte autour (ex: "Je mise 10."), on utilise une Regex
            match = re.search(r"\d+", content)
            if match:
                val = int(match.group())
                # Sécurité : on borne entre 0 et endowment
                return max(0, min(val, endowment))
            else:
                # Si l'IA raconte n'importe quoi sans chiffre, on joue la sécurité (0 ou aléatoire)
                return random.randint(0, endowment)

        except Exception as e:
            print(f"Erreur Ollama ({self.model_name}): {e}")
            return 0  # En cas de crash technique, on ne mise rien


# --- MOTEUR DE SIMULATION (Identique à l'étape précédente) ---


def play_public_goods_game(players_strategies, config):
    history_global = []
    dataset = []
    n_players = len(players_strategies)
    cumulative_scores = {i: 0 for i in range(n_players)}

    # Affichage pour suivre la vitesse (l'IA peut être lente)
    print(f"🎮 Démarrage partie : {n_players} joueurs (dont IA)...")

    for round_num in range(1, config["n_rounds"] + 1):
        current_contributions = {}

        # Phase de Décision
        for pid, strategy in enumerate(players_strategies):
            contribution = strategy.decide_contribution(
                history_global, pid, config["endowment"]
            )
            contribution = max(0, min(contribution, config["endowment"]))
            current_contributions[pid] = contribution

        # Calculs
        total_pot = sum(current_contributions.values())
        multiplied_pot = total_pot * config["multiplier"]
        share_per_player = multiplied_pot / n_players

        history_global.append(
            {
                "round": round_num,
                "contributions": current_contributions,
                "total_pot": total_pot,
            }
        )

        for pid, strategy in enumerate(players_strategies):
            kept = config["endowment"] - current_contributions[pid]
            round_gain = kept + share_per_player
            cumulative_scores[pid] += round_gain

            dataset.append(
                {
                    "round": round_num,
                    "player_id": pid,
                    "strategy": strategy.get_name(),
                    "endowment": config["endowment"],
                    "contribution": current_contributions[pid],
                    "kept_private": kept,
                    "pot_share_received": round_gain - kept,
                    "round_gain_total": round_gain,
                    "cumulative_score": cumulative_scores[pid],
                    "group_total_pot": total_pot,
                    "group_synergy_factor": config["multiplier"],
                }
            )

    return dataset


# --- TEST RAPIDE (Si exécuté directement) ---

if __name__ == "__main__":
    # Assure-toi que ce modèle est installé (ex: ollama pull mistral)
    # 'mistral' ou 'gemma2' sont souvent meilleurs que llama3 pour suivre des instructions complexes en français.
    MODEL_TO_USE = "gemma2"

    print(f"--- Démarrage du tournoi IA avec le modèle {MODEL_TO_USE} ---")

    players = [
        # Joueur 1 : L'Altruiste nuancé
        LLMStrategy(model_name=MODEL_TO_USE, persona="altruist"),
        # Joueur 2 : Le Profiteur intelligent
        LLMStrategy(model_name=MODEL_TO_USE, persona="greedy"),
        # Joueur 3 : L'Équilibré (la balance)
        LLMStrategy(model_name=MODEL_TO_USE, persona="adaptive"),
        # Joueur 4 : Un humain codé (Conditional) pour servir de "témoin" stable
        ConditionalCooperator(),
    ]

    # On lance une partie de 10 tours (suffisant pour voir la dynamique sans attendre 10 min)
    GAME_CONFIG["n_rounds"] = 20

    data = play_public_goods_game(players, GAME_CONFIG)

    # Petit affichage console pour vérifier la logique
    df = pd.DataFrame(data)

    print("\n--- ANALYSE RAPIDE ---")
    # On regarde la moyenne des mises par stratégie
    print(df.groupby("strategy")["contribution"].mean().sort_values(ascending=False))
