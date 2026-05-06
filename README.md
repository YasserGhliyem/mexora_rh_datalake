# Miniprojet 2 — Data Lake & Analyse du Marché de l'Emploi IT au Maroc

Ce projet implémente une architecture Data Lake (Bronze, Silver, Gold) pour analyser le marché de l'emploi IT au Maroc, avec un pipeline ETL en Python et des analyses via DuckDB.

## 🚀 Comment lancer le projet ?

### 1. Installation des dépendances
Installez les bibliothèques requises :
pip install -r requirements.txt

### 2. Génération des données brutes
Générez les fichiers de données avec les erreurs intentionnelles :
python data_generator_p2.py

### 3. Exécution du Pipeline ETL
Lancez le pipeline qui va créer le Data Lake et remplir les zones Bronze, Silver et Gold :
python main.py

### 4. Analyse et Dashboard
Ouvrez et exécutez le notebook `analyse_marche_it_maroc.ipynb` pour visualiser les insights métier via DuckDB.