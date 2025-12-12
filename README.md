# 🧬 Simulation : Jeu du Bien Public (IA vs Algorithmes)

> **"Coopérer ou Trahir ?"** — Une réinterprétation moderne de l'expérience d'Axelrod (1981) utilisant des LLMs locaux (Ollama) et une architecture de données moderne (Parquet/DuckDB).

## 📋 Contexte du Projet

Ce projet vise à simuler des interactions sociales complexes à travers le **Jeu du Bien Public** (Public Goods Game). Il compare deux types d'agents :
1.  **Algorithmes Codés** (Stratégies classiques : *Tit-for-Tat*, *Free Rider*, *Altruist*).
2.  **Agents IA Génératifs** (LLMs via Ollama : *Gemma2, Gemma3*) dotés de personnalités psychologiques (*Greedy*, *Adaptive*, *Altruist*).

---

## 🛠️ Stack Technique

* **Langage** : Python 3.10+
* **IA Générative** : [Ollama](https://ollama.com/) (Local LLM inference)
* **Stockage** : Format [Parquet](https://parquet.apache.org/) (Colonnes, compressé)
* **Analyse SQL** : [DuckDB](https://duckdb.org/) (OLAP in-process)
* **Visualisation** : [Streamlit](https://streamlit.io/) & [Plotly](https://plotly.com/)

---

## 📂 Structure du Projet

```bash

├── AI/                             # 🤖 Partie Simulation avec Agents IA (LLMs)
│   ├── data_gemma3/                # Données générées par le modèle (ex: Gemma 3)
│   │   ├── simulation_ia_results1.parquet  # Scénario 1
│   │   ├── simulation_ia_results2.parquet  # Scénario 2
│   │   └── ...
│   ├── createData.py               # Script ETL pour lancer les scénarios IA
│   ├── mainGame.py                 # Moteur du jeu et Prompts (Personas)
│   └── streamlit.py                # Dashboard d'analyse spécifique IA
│
├── Not_AI/                         # 🧮 Partie Simulation Algorithmique (Code classique)
│   ├── createData.py               # Script de génération des données témoins
│   ├── mainGame.py                 # Logique du jeu (Stratégies codées en dur)
│   ├── simulation_results.parquet  # Dataset des stratégies classiques
│   └── streamlit.py                # Dashboard d'analyse classique
│
├── .gitignore
└── README.md                       # Documentation

```

## 🚀 Utilisation

### **🔍 Tests Rapides (Terminal)**
On peut lancer uniquement les **`mainGame.py`** pour avoir le résultat dans le terminal, pratique pour les tests.

---

### **📦 Génération de Données (Parquet)**
En utilisant **`createData.py`**, on lancera le jeu mais ça stockera les données du jeu dans des fichiers **`.parquet`** dans un dossier `data/` (nous avons ensuite trié à la main les fichiers dans les bons dossiers).

---

### **📊 Visualisation & Analyse (Streamlit)**
Pour finir, les fichiers **`streamlit.py`** permettent de lancer un streamlit afin de visualiser/analyser les données.