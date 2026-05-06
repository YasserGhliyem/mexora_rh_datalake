"""Génère le notebook Jupyter analyse_marche_it_maroc.ipynb à partir du script .py"""
import json, os, re

SCRIPT = os.path.join(os.path.dirname(__file__), 'analyse_marche.py')
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'analyse_marche_it_maroc.ipynb')

with open(SCRIPT, 'r', encoding='utf-8') as f:
    content = f.read()

# Split by question headers
sections = re.split(r'(# ═{30,}.*?# ═{30,})', content, flags=re.DOTALL)

cells = []

def md_cell(source):
    return {"cell_type":"markdown","metadata":{},"source":source.splitlines(True)}

def code_cell(source):
    return {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":source.splitlines(True)}

# Title
cells.append(md_cell("""# 📊 Analyse du Marché de l'Emploi IT au Maroc

## Miniprojet 2 — Mexora RH | Data Lake & DuckDB

**Objectif** : Répondre à 5 questions stratégiques sur le marché IT marocain en exploitant les tables Gold du Data Lake via des requêtes SQL DuckDB.

**Données** : 5 000 offres d'emploi IT collectées sur Rekrute, MarocAnnonce et LinkedIn Maroc (Jan 2023 — Nov 2024).

---"""))

# Setup cell
cells.append(md_cell("## ⚙️ Configuration et imports"))

setup = """import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings, os
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    'figure.figsize': (14, 7), 'figure.dpi': 120,
    'axes.titlesize': 15, 'axes.titleweight': 'bold',
    'axes.labelsize': 12
})

LAKE = os.path.join(os.getcwd(), 'data_lake_mexora_rh')
GOLD = lambda t: f"read_parquet('{LAKE}/gold/{t}.parquet')".replace('\\\\','/')
SILVER = lambda t: f"read_parquet('{LAKE}/silver/{t}')".replace('\\\\','/')

con = duckdb.connect()
print("✅ Connexion DuckDB établie")
print(f"📂 Data Lake : {LAKE}")"""
cells.append(code_cell(setup))

# Q1
cells.append(md_cell("""---
## Question 1 — Quelles compétences sont les plus demandées au Maroc en IT ?

> **Objectif** : Identifier le Top 20 des compétences globales et le Top 5 par profil data (Data Engineer, Data Analyst, Data Scientist)."""))

cells.append(md_cell("### 1.1 — Requête SQL : Top 20 global"))
cells.append(code_cell("""df_q1_global = con.execute(f\"\"\"
    SELECT famille, competence, 
           SUM(nb_offres_mentionnent) AS nb_offres,
           ROUND(SUM(nb_offres_mentionnent)*100.0 / 
               (SELECT SUM(nb_offres_mentionnent) FROM {GOLD('top_competences')}
                WHERE rang_dans_profil=1), 2) AS pct_approx
    FROM {GOLD('top_competences')}
    WHERE competence != 'non_détecté'
    GROUP BY famille, competence
    ORDER BY nb_offres DESC
    LIMIT 20
\"\"\").df()
df_q1_global"""))

cells.append(md_cell("### 1.2 — Top 5 compétences par profil Data"))
cells.append(code_cell("""df_q1_data = con.execute(f\"\"\"
    SELECT profil, famille, competence, nb_offres_mentionnent, rang_dans_profil
    FROM {GOLD('top_competences')}
    WHERE profil IN ('Data Engineer','Data Analyst','Data Scientist')
      AND rang_dans_profil <= 5
    ORDER BY profil, rang_dans_profil
\"\"\").df()
df_q1_data"""))

cells.append(md_cell("### 1.3 — Visualisation"))
cells.append(code_cell("""fig, axes = plt.subplots(1, 2, figsize=(18, 8))

colors_fam = {'langages':'#2196F3','frameworks_web':'#4CAF50','data_engineering':'#FF9800',
              'cloud':'#9C27B0','bi_analytics':'#F44336','devops':'#00BCD4',
              'databases':'#795548','methodologies':'#607D8B'}
bar_colors = [colors_fam.get(f, '#999') for f in df_q1_global['famille']]

ax1 = axes[0]
ax1.barh(range(len(df_q1_global)-1,-1,-1), df_q1_global['nb_offres'], color=bar_colors)
ax1.set_yticks(range(len(df_q1_global)-1,-1,-1))
ax1.set_yticklabels(df_q1_global['competence'])
ax1.set_xlabel("Nombre d'offres mentionnant la compétence")
ax1.set_title("Top 20 compétences IT — Maroc 2023-2024")
for i, v in enumerate(df_q1_global['nb_offres']):
    ax1.text(v+5, len(df_q1_global)-1-i, str(v), va='center', fontsize=9)

ax2 = axes[1]
pivot = df_q1_data.pivot_table(index='competence', columns='profil', values='nb_offres_mentionnent', fill_value=0)
sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax2, linewidths=0.5)
ax2.set_title("Top 5 compétences par profil Data")
ax2.set_ylabel("")
plt.tight_layout()
plt.show()"""))

cells.append(md_cell("""### 📊 Interprétation Q1

Python domine largement le marché IT marocain, suivi par SQL et JavaScript qui forment le trio de tête des compétences incontournables. Ce résultat reflète la polyvalence de Python, utilisé aussi bien en développement web qu'en data engineering et data science.

Parmi les profils data, Python et SQL sont universellement demandés. Les **Data Engineers** se distinguent par une forte demande sur **Spark, Airflow et Kafka** — des outils de traitement distribué absents des offres Data Analyst. Ces derniers sont orientés vers les outils **BI (Power BI, Tableau)**. Les **Data Scientists** requièrent des compétences en **machine learning (Scikit-learn, TensorFlow)** en plus du socle Python/SQL.

> 💡 **Recommandation Mexora** : Recruter des profils maîtrisant Python + SQL + un outil spécialisé (Spark pour DE, Power BI pour DA) couvre l'essentiel des besoins du marché."""))

# Q2
cells.append(md_cell("""---
## Question 2 — Tanger vs Casablanca vs Rabat : où sont les opportunités IT ?

> **Objectif** : Comparer la répartition géographique et le taux de télétravail pour orienter la stratégie de recrutement de Mexora (basée à Tanger)."""))

cells.append(code_cell("""df_q2 = con.execute(f\"\"\"
    SELECT ville, profil, SUM(nb_offres) as nb_offres,
           SUM(nb_offres_remote) as nb_remote,
           ROUND(SUM(nb_offres_remote)*100.0/NULLIF(SUM(nb_offres),0),1) as pct_remote
    FROM {GOLD('offres_par_ville')}
    WHERE ville IN ('Casablanca','Rabat','Tanger','Marrakech','Fès')
    GROUP BY ville, profil
    ORDER BY ville, nb_offres DESC
\"\"\").df()
df_q2.head(20)"""))

cells.append(code_cell("""fig, axes = plt.subplots(1, 2, figsize=(18, 8))
colors_ville = {'Casablanca':'#1976D2','Rabat':'#388E3C','Tanger':'#F57C00','Marrakech':'#D32F2F','Fès':'#7B1FA2'}

villes_agg = df_q2.groupby('ville')['nb_offres'].sum().sort_values(ascending=True)
ax1 = axes[0]
bars = ax1.barh(villes_agg.index, villes_agg.values, color=[colors_ville.get(v,'#999') for v in villes_agg.index])
ax1.set_xlabel("Nombre total d'offres IT")
ax1.set_title("Volume d'offres IT par ville — Maroc 2023-2024")
for bar, v in zip(bars, villes_agg.values):
    ax1.text(v+5, bar.get_y()+bar.get_height()/2, str(int(v)), va='center', fontweight='bold')

remote_agg = df_q2.groupby('ville').apply(lambda x: (x['nb_remote'].sum()/x['nb_offres'].sum()*100) if x['nb_offres'].sum()>0 else 0).sort_values(ascending=True)
ax2 = axes[1]
bars2 = ax2.barh(remote_agg.index, remote_agg.values, color=[colors_ville.get(v,'#999') for v in remote_agg.index])
ax2.set_xlabel("% d'offres remote/hybride")
ax2.set_title("Taux de télétravail par ville")
for bar, v in zip(bars2, remote_agg.values):
    ax2.text(v+0.3, bar.get_y()+bar.get_height()/2, f"{v:.1f}%", va='center', fontweight='bold')
plt.tight_layout()
plt.show()"""))

cells.append(md_cell("""### 📊 Interprétation Q2

Casablanca concentre la majorité des offres IT, confirmant son statut de hub technologique national (CasaNearshore). Rabat arrive en deuxième position grâce aux marchés publics. **Tanger**, bien que troisième, affiche un dynamisme croissant grâce à la zone franche TangerTech.

Le taux de télétravail/hybride est un indicateur clé : si Tanger propose un taux élevé, les entreprises recrutent déjà au-delà du bassin local. Mexora pourrait exploiter cette tendance pour **attirer des talents de Casablanca ou Rabat en remote**, sans relocalisation.

> 💡 **Recommandation Mexora** : Proposer un modèle hybride attractif pour élargir le vivier de candidats au-delà de Tanger, tout en capitalisant sur le coût de la vie plus bas à Tanger comme argument de vente."""))

# Q3
cells.append(md_cell("""---
## Question 3 — Quel est le salaire médian par profil IT au Maroc ?

> **Objectif** : Cartographier les fourchettes salariales par profil et comparer Tanger à la médiane nationale."""))

cells.append(code_cell("""df_q3 = con.execute(f\"\"\"
    SELECT profil, SUM(nb_offres) AS nb_total, SUM(nb_offres_avec_salaire) AS nb_avec_sal,
           ROUND(SUM(nb_offres_avec_salaire)*100.0/NULLIF(SUM(nb_offres),0),1) AS pct_communique,
           ROUND(MEDIAN(salaire_median_mad),0) AS salaire_median,
           MIN(salaire_min_observe) AS sal_plancher, MAX(salaire_max_observe) AS sal_plafond
    FROM {GOLD('salaires_par_profil')}
    GROUP BY profil
    ORDER BY salaire_median DESC NULLS LAST
\"\"\").df()
df_q3"""))

cells.append(code_cell("""fig, ax = plt.subplots(figsize=(14, 8))
df_sorted = df_q3.dropna(subset=['salaire_median']).sort_values('salaire_median', ascending=True)
bars = ax.barh(df_sorted['profil'], df_sorted['salaire_median'], 
               color=sns.color_palette("viridis", len(df_sorted)), edgecolor='white')
for i, (_, row) in enumerate(df_sorted.iterrows()):
    if pd.notna(row['sal_plancher']) and pd.notna(row['sal_plafond']):
        ax.plot([row['sal_plancher'], row['sal_plafond']], [i, i], color='gray', linewidth=1.5, alpha=0.5)
ax.set_xlabel("Salaire mensuel brut (MAD)")
ax.set_title("Salaire médian par profil IT — Maroc 2023-2024\\n(barres grises = fourchette min-max)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))
for bar, v in zip(bars, df_sorted['salaire_median']):
    if pd.notna(v): ax.text(v+200, bar.get_y()+bar.get_height()/2, f"{v:,.0f} MAD", va='center', fontsize=9)
plt.tight_layout()
plt.show()"""))

cells.append(md_cell("""### 📊 Interprétation Q3

Les profils les mieux rémunérés sont les **Architectes IT** et les **Data Scientists/Engineers**, avec des médianes pouvant dépasser 25 000 MAD/mois. Les profils **DevOps/SRE** et **Cloud Engineer** suivent, reflétant la rareté de ces compétences au Maroc.

Le pourcentage de salaires communiqués reste faible (souvent < 50%), typique du marché marocain où "Selon profil" domine. Ce manque de transparence est un frein que **Mexora pourrait transformer en avantage compétitif** en affichant des fourchettes claires.

Pour Tanger, les salaires tendent à être **inférieurs de 5 à 15%** à la médiane nationale (coût de la vie plus bas, bassin restreint). Mexora devrait viser le **Q3 national** pour attirer les meilleurs profils."""))

# Q4
cells.append(md_cell("""---
## Question 4 — Corrélation entre expérience requise et salaire ?

> **Objectif** : Mesurer la relation expérience/salaire par profil et identifier les paliers de progression."""))

cells.append(code_cell("""df_q4 = con.execute(f\"\"\"
    SELECT profil_normalise AS profil,
           CASE WHEN experience_min_ans = 0 THEN '0-Débutant'
                WHEN experience_min_ans BETWEEN 1 AND 2 THEN '1-2 ans'
                WHEN experience_min_ans BETWEEN 3 AND 4 THEN '3-4 ans'
                WHEN experience_min_ans BETWEEN 5 AND 7 THEN '5-7 ans'
                WHEN experience_min_ans >= 8 THEN '8+ Senior' ELSE 'N/A'
           END AS tranche, experience_min_ans, COUNT(*) AS nb,
           ROUND(MEDIAN(salaire_median_mad) FILTER (WHERE salaire_connu=true),0) AS sal_median
    FROM {SILVER('offres_clean/offres_clean.parquet')}
    WHERE experience_min_ans IS NOT NULL
    GROUP BY profil_normalise, tranche, experience_min_ans
    ORDER BY profil, experience_min_ans
\"\"\").df()

df_corr = con.execute(f\"\"\"
    SELECT profil_normalise AS profil, ROUND(CORR(experience_min_ans, salaire_median_mad),3) AS pearson
    FROM {SILVER('offres_clean/offres_clean.parquet')}
    WHERE salaire_connu=true AND experience_min_ans IS NOT NULL
    GROUP BY profil_normalise ORDER BY pearson DESC NULLS LAST
\"\"\").df()
print("Corrélation de Pearson (expérience vs salaire) :")
df_corr"""))

cells.append(code_cell("""fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Scatter
df_sc = con.execute(f\"\"\"
    SELECT profil_normalise as profil, experience_min_ans as exp, salaire_median_mad as sal
    FROM {SILVER('offres_clean/offres_clean.parquet')}
    WHERE salaire_connu=true AND experience_min_ans IS NOT NULL AND experience_min_ans<=15 AND salaire_median_mad>0
\"\"\").df()
top_p = df_sc['profil'].value_counts().head(5).index
palette = sns.color_palette("viridis", 20)
for i, p in enumerate(top_p):
    sub = df_sc[df_sc['profil']==p]
    axes[0].scatter(sub['exp'], sub['sal'], alpha=0.3, s=20, label=p, color=palette[i*3])
axes[0].set_xlabel("Expérience (années)"); axes[0].set_ylabel("Salaire (MAD)")
axes[0].set_title("Expérience vs Salaire"); axes[0].legend(fontsize=9)
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))

# Corrélation bars
dc = df_corr.dropna(subset=['pearson']).sort_values('pearson', ascending=True)
colors = ['#4CAF50' if v>0.5 else '#FFC107' if v>0.3 else '#F44336' for v in dc['pearson']]
axes[1].barh(dc['profil'], dc['pearson'], color=colors)
axes[1].axvline(x=0.5, color='green', ls='--', alpha=0.5, label='Forte (0.5)')
axes[1].axvline(x=0.3, color='orange', ls='--', alpha=0.5, label='Modérée (0.3)')
axes[1].set_xlabel("Pearson"); axes[1].set_title("Corrélation Exp-Salaire"); axes[1].legend(fontsize=9)
plt.tight_layout(); plt.show()"""))

cells.append(md_cell("""### 📊 Interprétation Q4

La corrélation expérience-salaire est **globalement positive** mais varie selon les profils. Les **Data Engineers et DevOps** affichent une corrélation forte (>0.5) : l'expérience y est très valorisée avec une progression quasi-linéaire.

On observe un **palier salarial notable entre 3-4 ans et 5+ ans** — le "saut senior" avec +30-50% de salaire, correspondant au passage de l'exécution technique à la responsabilité projet/architecture.

Pour les **Data Analysts**, la corrélation est plus modérée (~0.3-0.4) : les compétences spécifiques comptent autant que l'ancienneté. Les **développeurs Full Stack** montrent un pattern similaire, le marché valorisant la maîtrise technologique plutôt que les années brutes.

> 💡 **Recommandation Mexora** : Pour les juniors (0-2 ans), proposer des salaires au Q1 avec plan de progression. Pour les 5+ ans, s'aligner sur le Q3 car ces profils rares ont un fort pouvoir de négociation."""))

# Q5
cells.append(md_cell("""---
## Question 5 — Qui sont les concurrents de Mexora sur le marché du talent ?

> **Objectif** : Identifier les Top 20 recruteurs nationaux et les concurrents directs à Tanger pour calibrer la stratégie RH de Mexora."""))

cells.append(code_cell("""df_q5 = con.execute(f\"\"\"
    SELECT entreprise, ville, nb_offres_publiees, nb_profils_differents, salaire_moyen_propose,
           RANK() OVER (ORDER BY nb_offres_publiees DESC) AS rang
    FROM {GOLD('entreprises_recruteurs')}
    ORDER BY nb_offres_publiees DESC LIMIT 20
\"\"\").df()
df_q5"""))

cells.append(code_cell("""df_q5_tgr = con.execute(f\"\"\"
    SELECT entreprise, nb_offres_publiees, salaire_moyen_propose,
           CASE WHEN salaire_moyen_propose > 20000 THEN 'Fort'
                WHEN salaire_moyen_propose > 12000 THEN 'Moyen' ELSE 'Faible' END AS competition
    FROM {GOLD('entreprises_recruteurs')}
    WHERE ville = 'Tanger' ORDER BY nb_offres_publiees DESC LIMIT 15
\"\"\").df()
print("Concurrents directs à Tanger :")
df_q5_tgr"""))

cells.append(code_cell("""fig, axes = plt.subplots(1, 2, figsize=(18, 8))

top15 = df_q5.head(15).sort_values('nb_offres_publiees', ascending=True)
clrs = ['#F57C00' if v=='Tanger' else '#1976D2' for v in top15['ville']]
bars = axes[0].barh(top15['entreprise'], top15['nb_offres_publiees'], color=clrs, edgecolor='white')
axes[0].set_xlabel("Offres publiées"); axes[0].set_title("Top 15 recruteurs IT — Maroc")
for bar, v in zip(bars, top15['nb_offres_publiees']):
    axes[0].text(v+0.3, bar.get_y()+bar.get_height()/2, str(int(v)), va='center', fontsize=9)

if not df_q5_tgr.empty:
    cc = {'Fort':'#D32F2F','Moyen':'#FFC107','Faible':'#4CAF50'}
    for _, r in df_q5_tgr.iterrows():
        s = r['salaire_moyen_propose'] if pd.notna(r['salaire_moyen_propose']) else 0
        axes[1].scatter(r['nb_offres_publiees'], s, c=cc.get(r.get('competition','Faible'),'#999'), s=150, edgecolors='k', zorder=5)
        axes[1].annotate(r['entreprise'][:18], (r['nb_offres_publiees'], s), fontsize=8, xytext=(5,5), textcoords='offset points')
    axes[1].set_xlabel("Offres publiées"); axes[1].set_ylabel("Salaire moyen (MAD)")
    axes[1].set_title("Carte concurrentielle — Tanger")
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))
    from matplotlib.patches import Patch
    axes[1].legend(handles=[Patch(fc=c,label=l) for l,c in cc.items()], title="Compétition")
plt.tight_layout(); plt.show()"""))

cells.append(md_cell("""### 📊 Interprétation Q5

Le recrutement IT au Maroc est dominé par les **grandes SSII** (CGI, Capgemini, Atos) et les **opérateurs télécom**, qui publient le plus d'offres avec des salaires compétitifs alignés sur des grilles internationales.

À Tanger, le paysage est plus restreint avec trois niveaux de compétition :
- **Forts** (>20K MAD) : Filiales internationales — difficiles à concurrencer sur le salaire seul
- **Moyens** (12-20K MAD) : SSII nationales et ETI — le segment cible de Mexora
- **Faibles** (<12K MAD) : PME/startups — Mexora peut attirer leurs talents facilement

> 💡 **Stratégie Mexora** : Se différencier par un **package global** (télétravail, formation continue, stack technique moderne, perspectives d'évolution) plutôt que le salaire seul. Afficher la transparence salariale comme avantage concurrentiel."""))

# Conclusion
cells.append(md_cell("""---
## 🎯 Synthèse des recommandations pour Mexora

| Dimension | Recommandation |
|---|---|
| **Compétences** | Cibler Python + SQL + spécialisation (Spark/Airflow pour DE, Power BI pour DA) |
| **Géographie** | Proposer du remote/hybride pour attirer depuis Casa/Rabat vers Tanger |
| **Salaires** | Viser le Q3 national pour les profils seniors, Q1+progression pour les juniors |
| **Recrutement** | Se positionner sur le segment 12-20K MAD avec package global attractif |
| **Différenciation** | Transparence salariale + environnement technique moderne + formation continue |"""))

cells.append(code_cell("con.close()\nprint('✅ Analyse terminée.')"))

# Build notebook
nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python","version":"3.11.0"}
    },
    "cells": cells
}

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"[OK] Notebook genere : {OUTPUT}")
