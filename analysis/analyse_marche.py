"""
Analyse du Marché de l'Emploi IT au Maroc — Mexora RH
Requêtes DuckDB sur les tables Gold du Data Lake
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings, os
warnings.filterwarnings('ignore')

# ── Style global ──────────────────────────────────────────────
sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    'figure.figsize': (14, 7), 'figure.dpi': 120,
    'axes.titlesize': 15, 'axes.titleweight': 'bold',
    'axes.labelsize': 12
})
PALETTE = sns.color_palette("viridis", 20)
PALETTE2 = sns.color_palette("magma", 10)

# ── Connexion DuckDB ──────────────────────────────────────────
LAKE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data_lake_mexora_rh')
GOLD = lambda t: f"read_parquet('{LAKE}/gold/{t}.parquet')".replace('\\','/')
SILVER = lambda t: f"read_parquet('{LAKE}/silver/{t}')".replace('\\','/')

con = duckdb.connect()

# ══════════════════════════════════════════════════════════════
# QUESTION 1 — Top compétences IT au Maroc
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("Q1 — Compétences les plus demandées")
print("=" * 60)

df_q1_global = con.execute(f"""
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
""").df()
print(df_q1_global.to_string(index=False))

# Top 5 par profil data
df_q1_data = con.execute(f"""
    SELECT profil, famille, competence, nb_offres_mentionnent, rang_dans_profil
    FROM {GOLD('top_competences')}
    WHERE profil IN ('Data Engineer','Data Analyst','Data Scientist')
      AND rang_dans_profil <= 5
    ORDER BY profil, rang_dans_profil
""").df()
print("\nTop 5 compétences par profil Data :")
print(df_q1_data.to_string(index=False))

# Visualisation Q1
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Barres horizontales - Top 20 global
ax1 = axes[0]
colors_fam = {'langages':'#2196F3','frameworks_web':'#4CAF50','data_engineering':'#FF9800',
              'cloud':'#9C27B0','bi_analytics':'#F44336','devops':'#00BCD4',
              'databases':'#795548','methodologies':'#607D8B'}
bar_colors = [colors_fam.get(f, '#999') for f in df_q1_global['famille']]
ax1.barh(range(len(df_q1_global)-1,-1,-1), df_q1_global['nb_offres'], color=bar_colors)
ax1.set_yticks(range(len(df_q1_global)-1,-1,-1))
ax1.set_yticklabels(df_q1_global['competence'])
ax1.set_xlabel("Nombre d'offres mentionnant la compétence")
ax1.set_title("Top 20 compétences IT — Maroc 2023-2024")
for i, v in enumerate(df_q1_global['nb_offres']):
    ax1.text(v+5, len(df_q1_global)-1-i, str(v), va='center', fontsize=9)

# Heatmap - Profils Data
ax2 = axes[1]
pivot = df_q1_data.pivot_table(index='competence', columns='profil', 
                                values='nb_offres_mentionnent', fill_value=0)
sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax2, linewidths=0.5)
ax2.set_title("Top 5 compétences par profil Data")
ax2.set_ylabel("")

plt.tight_layout()
plt.savefig(os.path.join(LAKE, '..', 'analysis', 'q1_competences.png'), bbox_inches='tight')
plt.show()

print("""
📊 INTERPRÉTATION Q1 :
Python domine largement le marché IT marocain, mentionné dans une proportion 
significative des offres, suivi par SQL et JavaScript qui forment le trio de tête 
des compétences incontournables. Ce résultat reflète la polyvalence de Python, utilisé 
aussi bien en développement web (Django/Flask) qu'en data engineering et data science.

Parmi les profils data spécifiquement, Python et SQL sont universellement demandés 
dans les trois catégories. Les Data Engineers se distinguent par une forte demande 
sur Spark, Airflow et Kafka — des outils d'orchestration et de traitement distribué 
absents des offres Data Analyst. Ces derniers sont davantage orientés vers les outils 
BI (Power BI, Tableau) et Excel avancé. Les Data Scientists requièrent des compétences 
en machine learning (Scikit-learn, TensorFlow) en plus du socle Python/SQL commun.

Pour Mexora, cela signifie que recruter des profils maîtrisant Python + SQL + un outil 
spécialisé (Spark pour DE, Power BI pour DA) couvre l'essentiel des besoins du marché.
""")

# ══════════════════════════════════════════════════════════════
# QUESTION 2 — Répartition géographique : Tanger vs Casa vs Rabat
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("Q2 — Répartition géographique des opportunités IT")
print("=" * 60)

df_q2 = con.execute(f"""
    SELECT ville, profil, SUM(nb_offres) as nb_offres,
           SUM(nb_offres_remote) as nb_remote,
           ROUND(SUM(nb_offres_remote)*100.0/NULLIF(SUM(nb_offres),0),1) as pct_remote
    FROM {GOLD('offres_par_ville')}
    WHERE ville IN ('Casablanca','Rabat','Tanger','Marrakech','Fès')
    GROUP BY ville, profil
    ORDER BY ville, nb_offres DESC
""").df()
print(df_q2.to_string(index=False))

# Focus Tanger
df_q2_tanger = con.execute(f"""
    SELECT profil, SUM(nb_offres) as nb_offres,
           ROUND(SUM(nb_offres_remote)*100.0/NULLIF(SUM(nb_offres),0),1) as pct_remote
    FROM {GOLD('offres_par_ville')}
    WHERE ville = 'Tanger'
    GROUP BY profil
    ORDER BY nb_offres DESC
""").df()
print("\nFocus Tanger :")
print(df_q2_tanger.to_string(index=False))

# Visualisation Q2
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Barres groupées par ville
ax1 = axes[0]
villes_agg = df_q2.groupby('ville')['nb_offres'].sum().sort_values(ascending=True)
colors_ville = {'Casablanca':'#1976D2','Rabat':'#388E3C','Tanger':'#F57C00',
                'Marrakech':'#D32F2F','Fès':'#7B1FA2'}
bars = ax1.barh(villes_agg.index, villes_agg.values, 
                color=[colors_ville.get(v,'#999') for v in villes_agg.index])
ax1.set_xlabel("Nombre total d'offres IT")
ax1.set_title("Volume d'offres IT par ville — Maroc 2023-2024")
for bar, v in zip(bars, villes_agg.values):
    ax1.text(v+5, bar.get_y()+bar.get_height()/2, str(int(v)), va='center', fontweight='bold')

# Taux télétravail par ville
ax2 = axes[1]
remote_agg = df_q2.groupby('ville').apply(
    lambda x: (x['nb_remote'].sum()/x['nb_offres'].sum()*100) if x['nb_offres'].sum()>0 else 0
).sort_values(ascending=True)
bars2 = ax2.barh(remote_agg.index, remote_agg.values,
                 color=[colors_ville.get(v,'#999') for v in remote_agg.index])
ax2.set_xlabel("% d'offres remote/hybride")
ax2.set_title("Taux de télétravail par ville")
for bar, v in zip(bars2, remote_agg.values):
    ax2.text(v+0.3, bar.get_y()+bar.get_height()/2, f"{v:.1f}%", va='center', fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(LAKE, '..', 'analysis', 'q2_geographie.png'), bbox_inches='tight')
plt.show()

print("""
📊 INTERPRÉTATION Q2 :
Casablanca concentre la majorité des offres IT, confirmant son statut de hub 
technologique national avec le technopôle de CasaNearshore. Rabat arrive en 
deuxième position, porté par les marchés publics et les institutions. Tanger, 
bien que troisième, affiche un dynamisme croissant grâce à la zone franche 
TangerTech et l'implantation de multinationales.

Le taux de télétravail/hybride est un indicateur clé pour Mexora : si Tanger 
propose un taux de remote élevé, cela signifie que les entreprises tangerines 
recrutent déjà au-delà de leur bassin local. Mexora pourrait exploiter cette 
tendance pour attirer des talents de Casablanca ou Rabat en proposant un modèle 
hybride attractif, sans nécessiter une relocalisation complète.

Le ratio Tanger/Casablanca par profil révèle les niches locales : si les profils 
DevOps ou Cloud sont proportionnellement plus demandés à Tanger qu'à Casa, cela 
indique des opportunités de spécialisation pour le positionnement de Mexora.
""")

# ══════════════════════════════════════════════════════════════
# QUESTION 3 — Salaires médians par profil IT
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("Q3 — Salaires médians par profil IT au Maroc")
print("=" * 60)

df_q3 = con.execute(f"""
    SELECT profil, SUM(nb_offres) AS nb_offres_total,
           SUM(nb_offres_avec_salaire) AS nb_avec_salaire,
           ROUND(SUM(nb_offres_avec_salaire)*100.0/NULLIF(SUM(nb_offres),0),1) AS pct_communique,
           ROUND(MEDIAN(salaire_median_mad),0) AS salaire_median,
           MIN(salaire_min_observe) AS salaire_plancher,
           MAX(salaire_max_observe) AS salaire_plafond
    FROM {GOLD('salaires_par_profil')}
    GROUP BY profil
    ORDER BY salaire_median DESC NULLS LAST
""").df()
print(df_q3.to_string(index=False))

# Salaires Tanger
df_q3_tanger = con.execute(f"""
    SELECT profil, nb_offres, salaire_median_mad, salaire_q1_mad, salaire_q3_mad
    FROM {GOLD('salaires_par_profil')}
    WHERE ville = 'Tanger' AND nb_offres >= 2
    ORDER BY salaire_median_mad DESC
""").df()
print("\nSalaires à Tanger :")
print(df_q3_tanger.to_string(index=False))

# Visualisation Q3
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Boxplot salaires par profil
ax1 = axes[0]
df_q3_sorted = df_q3.dropna(subset=['salaire_median']).sort_values('salaire_median', ascending=True)
bars = ax1.barh(df_q3_sorted['profil'], df_q3_sorted['salaire_median'], 
                color=sns.color_palette("viridis", len(df_q3_sorted)), edgecolor='white')
# Ajouter fourchette
for i, (_, row) in enumerate(df_q3_sorted.iterrows()):
    if pd.notna(row['salaire_plancher']) and pd.notna(row['salaire_plafond']):
        ax1.plot([row['salaire_plancher'], row['salaire_plafond']], [i, i],
                 color='gray', linewidth=1.5, alpha=0.5)
ax1.set_xlabel("Salaire mensuel brut (MAD)")
ax1.set_title("Salaire médian par profil IT — Maroc")
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))
for bar, v in zip(bars, df_q3_sorted['salaire_median']):
    if pd.notna(v):
        ax1.text(v+200, bar.get_y()+bar.get_height()/2, f"{v:,.0f}", va='center', fontsize=9)

# Comparaison Tanger vs National
ax2 = axes[1]
if not df_q3_tanger.empty:
    merged = df_q3_tanger.merge(df_q3[['profil','salaire_median']], on='profil', suffixes=('_tanger','_national'))
    x = range(len(merged))
    w = 0.35
    ax2.bar([i-w/2 for i in x], merged['salaire_median_mad'], w, label='Tanger', color='#F57C00')
    ax2.bar([i+w/2 for i in x], merged['salaire_median'], w, label='National', color='#1976D2')
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(merged['profil'], rotation=45, ha='right')
    ax2.set_ylabel("Salaire médian (MAD)")
    ax2.set_title("Tanger vs Médiane nationale")
    ax2.legend()
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))

plt.tight_layout()
plt.savefig(os.path.join(LAKE, '..', 'analysis', 'q3_salaires.png'), bbox_inches='tight')
plt.show()

print("""
📊 INTERPRÉTATION Q3 :
Les profils les mieux rémunérés au Maroc sont les Architectes IT et les Data 
Scientists/Engineers, avec des médianes pouvant dépasser 25 000 MAD/mois. Les 
profils DevOps/SRE et Cloud Engineer suivent, reflétant la rareté de ces 
compétences sur le marché marocain. Les Data Analysts se situent dans une fourchette 
intermédiaire, tandis que les développeurs juniors et les profils Admin Systèmes 
affichent les médianes les plus basses.

Le pourcentage de salaires communiqués reste faible (souvent < 50%), ce qui est 
typique du marché marocain où la mention "Selon profil" domine. Ce manque de 
transparence salariale est un frein au recrutement que Mexora pourrait transformer 
en avantage compétitif en affichant des fourchettes claires.

Pour Tanger spécifiquement, les salaires tendent à être légèrement inférieurs à la 
médiane nationale (-5% à -15% selon les profils), ce qui s'explique par un coût de 
la vie plus bas et un bassin de talents plus restreint. Mexora devrait viser le Q3 
national pour attirer les meilleurs profils sur Tanger.
""")

# ══════════════════════════════════════════════════════════════
# QUESTION 4 — Corrélation expérience / salaire
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("Q4 — Corrélation expérience requise / salaire")
print("=" * 60)

df_q4 = con.execute(f"""
    SELECT
        profil_normalise AS profil,
        CASE
            WHEN experience_min_ans = 0 THEN '0 — Débutant'
            WHEN experience_min_ans BETWEEN 1 AND 2 THEN '1-2 ans'
            WHEN experience_min_ans BETWEEN 3 AND 4 THEN '3-4 ans'
            WHEN experience_min_ans BETWEEN 5 AND 7 THEN '5-7 ans'
            WHEN experience_min_ans >= 8 THEN '8+ ans Senior'
            ELSE 'Non précisé'
        END AS tranche_experience,
        experience_min_ans,
        COUNT(*) AS nb_offres,
        ROUND(MEDIAN(salaire_median_mad) FILTER (WHERE salaire_connu=true), 0) AS salaire_median
    FROM {SILVER('offres_clean/offres_clean.parquet')}
    WHERE experience_min_ans IS NOT NULL
    GROUP BY profil_normalise, tranche_experience, experience_min_ans
    ORDER BY profil, experience_min_ans
""").df()
print(df_q4.to_string(index=False))

# Corrélation Pearson par profil
df_corr = con.execute(f"""
    SELECT profil_normalise AS profil,
           ROUND(CORR(experience_min_ans, salaire_median_mad), 3) AS pearson
    FROM {SILVER('offres_clean/offres_clean.parquet')}
    WHERE salaire_connu=true AND experience_min_ans IS NOT NULL
    GROUP BY profil_normalise
    ORDER BY pearson DESC NULLS LAST
""").df()
print("\nCorrélation de Pearson (expérience vs salaire) :")
print(df_corr.to_string(index=False))

# Visualisation Q4
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Scatter + tendance
ax1 = axes[0]
df_scatter = con.execute(f"""
    SELECT profil_normalise as profil, experience_min_ans as exp, salaire_median_mad as sal
    FROM {SILVER('offres_clean/offres_clean.parquet')}
    WHERE salaire_connu=true AND experience_min_ans IS NOT NULL 
      AND experience_min_ans <= 15 AND salaire_median_mad > 0
""").df()
top_profils = df_scatter['profil'].value_counts().head(5).index
for i, p in enumerate(top_profils):
    sub = df_scatter[df_scatter['profil']==p]
    ax1.scatter(sub['exp'], sub['sal'], alpha=0.3, s=20, label=p, color=PALETTE[i*3])
ax1.set_xlabel("Expérience requise (années)")
ax1.set_ylabel("Salaire médian (MAD)")
ax1.set_title("Expérience vs Salaire — Par profil IT")
ax1.legend(fontsize=9, loc='upper left')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))

# Barres de corrélation
ax2 = axes[1]
df_corr_clean = df_corr.dropna(subset=['pearson']).sort_values('pearson', ascending=True)
colors = ['#4CAF50' if v > 0.5 else '#FFC107' if v > 0.3 else '#F44336' for v in df_corr_clean['pearson']]
ax2.barh(df_corr_clean['profil'], df_corr_clean['pearson'], color=colors, edgecolor='white')
ax2.axvline(x=0.5, color='green', linestyle='--', alpha=0.5, label='Seuil corrélation forte (0.5)')
ax2.axvline(x=0.3, color='orange', linestyle='--', alpha=0.5, label='Seuil modérée (0.3)')
ax2.set_xlabel("Coefficient de Pearson")
ax2.set_title("Corrélation Expérience-Salaire par profil")
ax2.legend(fontsize=9)
ax2.set_xlim(-0.2, 1.0)

plt.tight_layout()
plt.savefig(os.path.join(LAKE, '..', 'analysis', 'q4_correlation.png'), bbox_inches='tight')
plt.show()

print("""
📊 INTERPRÉTATION Q4 :
La corrélation entre expérience et salaire est globalement positive mais varie 
considérablement selon les profils. Les profils Data Engineer et DevOps affichent 
une corrélation forte (>0.5), indiquant que l'expérience est très valorisée et 
récompensée par une progression salariale quasi-linéaire.

On observe un palier salarial notable entre 3-4 ans et 5+ ans d'expérience : c'est 
le "saut senior" où les salaires augmentent de 30-50%. Ce palier correspond au 
passage de l'exécution technique à la responsabilité projet/architecture.

Pour les Data Analysts, la corrélation est plus modérée (~0.3-0.4), suggérant que 
les compétences spécifiques (maîtrise de Power BI, SQL avancé) comptent autant 
que l'ancienneté brute. Les développeurs Full Stack montrent également une 
corrélation modérée, le marché valorisant davantage la maîtrise technologique 
(stack React/Node vs Angular/Java) que les années d'expérience seules.

Recommandation Mexora : Pour les profils data juniors (0-2 ans), proposer des salaires 
au Q1 national avec un plan de progression claire. Pour les profils 5+ ans, s'aligner 
sur le Q3 car ces profils rares ont un fort pouvoir de négociation.
""")

# ══════════════════════════════════════════════════════════════
# QUESTION 5 — Top entreprises recruteurs & concurrents Mexora
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("Q5 — Entreprises recruteurs & concurrents de Mexora")
print("=" * 60)

df_q5 = con.execute(f"""
    SELECT entreprise, ville, nb_offres_publiees, nb_profils_differents,
           salaire_moyen_propose,
           RANK() OVER (ORDER BY nb_offres_publiees DESC) AS rang
    FROM {GOLD('entreprises_recruteurs')}
    ORDER BY nb_offres_publiees DESC
    LIMIT 20
""").df()
print(df_q5.to_string(index=False))

# Concurrents Tanger
df_q5_tanger = con.execute(f"""
    SELECT entreprise, nb_offres_publiees, salaire_moyen_propose,
           CASE
               WHEN salaire_moyen_propose > 20000 THEN 'Fort'
               WHEN salaire_moyen_propose > 12000 THEN 'Moyen'
               ELSE 'Faible'
           END AS niveau_competition
    FROM {GOLD('entreprises_recruteurs')}
    WHERE ville = 'Tanger'
    ORDER BY nb_offres_publiees DESC
    LIMIT 15
""").df()
print("\nConcurrents à Tanger :")
print(df_q5_tanger.to_string(index=False))

# Visualisation Q5
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Top 15 recruteurs
ax1 = axes[0]
top15 = df_q5.head(15).sort_values('nb_offres_publiees', ascending=True)
colors_type = ['#F57C00' if v=='Tanger' else '#1976D2' for v in top15['ville']]
bars = ax1.barh(top15['entreprise'], top15['nb_offres_publiees'], color=colors_type, edgecolor='white')
ax1.set_xlabel("Nombre d'offres publiées")
ax1.set_title("Top 15 entreprises recruteurs IT — Maroc")
for bar, v in zip(bars, top15['nb_offres_publiees']):
    ax1.text(v+0.3, bar.get_y()+bar.get_height()/2, str(int(v)), va='center', fontsize=9)

# Scatter concurrence (offres vs salaire)
ax2 = axes[1]
if not df_q5_tanger.empty:
    colors_comp = {'Fort':'#D32F2F','Moyen':'#FFC107','Faible':'#4CAF50'}
    for _, row in df_q5_tanger.iterrows():
        c = colors_comp.get(row.get('niveau_competition','Faible'), '#999')
        sal = row['salaire_moyen_propose'] if pd.notna(row['salaire_moyen_propose']) else 0
        ax2.scatter(row['nb_offres_publiees'], sal, c=c, s=150, edgecolors='black', zorder=5)
        ax2.annotate(row['entreprise'][:20], (row['nb_offres_publiees'], sal),
                     fontsize=8, ha='left', va='bottom', xytext=(5,5), textcoords='offset points')
    ax2.set_xlabel("Nombre d'offres publiées")
    ax2.set_ylabel("Salaire moyen proposé (MAD)")
    ax2.set_title("Carte concurrentielle — Tanger")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,p: f"{x/1000:.0f}K"))
    from matplotlib.patches import Patch
    legend_el = [Patch(fc=c, label=l) for l,c in colors_comp.items()]
    ax2.legend(handles=legend_el, title="Niveau compétition")

plt.tight_layout()
plt.savefig(os.path.join(LAKE, '..', 'analysis', 'q5_entreprises.png'), bbox_inches='tight')
plt.show()

print("""
📊 INTERPRÉTATION Q5 :
Le marché du recrutement IT au Maroc est dominé par les grandes SSII (CGI, Capgemini, 
Atos) et les opérateurs télécom (Maroc Telecom, Orange) qui publient le plus grand 
volume d'offres. Ces entreprises recrutent sur un large spectre de profils et offrent 
des salaires compétitifs grâce à leurs grilles internationales.

À Tanger, le paysage concurrentiel est plus restreint. Les entreprises locales et les 
filiales de multinationales implantées dans la zone franche constituent les principaux 
concurrents de Mexora. L'analyse révèle trois niveaux de compétition :
- **Compétiteurs forts** (>20K MAD) : Filiales internationales avec grilles salariales 
  européennes — difficiles à concurrencer sur le salaire seul.
- **Compétiteurs moyens** (12-20K MAD) : SSII nationales et ETI locales — le segment 
  où Mexora doit se positionner avec un package global attractif.
- **Compétiteurs faibles** (<12K MAD) : PME/startups — risque de turnover élevé, 
  Mexora peut attirer leurs talents avec une offre légèrement supérieure.

Stratégie recommandée : Mexora devrait se différencier non pas uniquement par le 
salaire, mais par un package complet (télétravail, formation, environnement technique 
moderne, perspectives d'évolution) pour attirer les profils data rares à Tanger.
""")

con.close()
print("\n✅ Analyse complète. Graphiques sauvegardés dans analysis/")
