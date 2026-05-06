# Rapport de Pipeline — Transformations Appliquées

**Date d'exécution** : 2026-05-06 21:12:41

---

## Bronze — Ingestion

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `offres_raw` | Partitionnement par source et par mois, sans transformation | 5150 | 5150 | 63 partitions créées, 3 sources, 246 dates invalides |
## Silver — Déduplication

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `id_offre` | drop_duplicates sur id_offre | 5150 | 5000 | 150 doublons supprimés |
## Silver — Normalisation Villes

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `ville` | Mapping dictionnaire → noms standards + région | 7 | 5 | 7 → 5 villes uniques |
## Silver — Normalisation Titres

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `titre_poste` | Mapping regex → profils IT normalisés | 5000 | 5000 | 4434 classés (88.7%), 566 'Autre IT' |
## Silver — Normalisation Salaires

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `salaire_brut` | Parsing fourchettes, K→×1000, EUR→MAD, validation plage | 5000 | 5000 | 2881 salaires valides (57.6%), 2119 non renseignés/invalides |
## Silver — Normalisation Expérience

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `experience_requise` | Parsing texte libre → années min/max | 5000 | 5000 | 4156 valeurs parsées (83.1%) |
## Silver — Normalisation Contrats

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `type_contrat` | Mapping dictionnaire → types standards | 5 | 2 | 5 → 2 types uniques |
## Silver — Nettoyage Dates

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `date_publication / date_expiration` | Conversion datetime, correction incohérences | 5000 | 5000 | 0 dates inversées, 240 dates nulles |
## Silver NLP — Extraction Compétences

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `description + competences_brut` | Matching regex word-boundary sur référentiel IT | 5000 | 22069 | 5000/5000 offres avec compétences, 22069 détections totales, moy 4.4/offre, 0 sans compétence |
## Gold — Top Compétences

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `top_competences` | Agrégation compétences par profil avec ranking | 0 | 84 | 12 compétences uniques |
## Gold — Salaires par Profil

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `salaires_par_profil` | Statistiques salariales (médiane, Q1, Q3, min, max) par profil/ville | 0 | 70 | 7 profils, 5 villes |
## Gold — Offres par Ville

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `offres_par_ville` | Volume d'offres par ville/profil/mois avec taux télétravail | 0 | 728 | 5 villes, pct_remote moyen: 75.1% |
## Gold — Top Entreprises

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `entreprises_recruteurs` | Top 100 entreprises par volume d'offres (min 2) | 0 | 25 | 25 entreprises, max offres: 466 |
## Gold — Tendances Mensuelles

| Champ | Règle appliquée | Avant | Après | Détails |
|---|---|---|---|---|
| `tendances_mensuelles` | Évolution mensuelle des offres par profil avec LAG | 0 | 140 | 2 années, 7 profils |

---

*Rapport auto-généré par le pipeline Mexora RH.*
