"""
silver_transform.py — Nettoyage et standardisation Bronze → Silver.

Transformations appliquées :
  1. Normalisation des villes (casa → Casablanca)
  2. Standardisation des titres de poste → profils IT normalisés
  3. Normalisation des salaires (K, EUR, fourchettes → MAD)
  4. Normalisation de l'expérience (texte libre → années min/max)
  5. Standardisation des types de contrats
  6. Nettoyage des dates (formats mixtes, cohérence publication/expiration)
  7. Ajout de colonnes dérivées (région, année, mois)
"""

import pandas as pd
import re
import json
from pathlib import Path
from datetime import datetime

from pipeline.utils import (
    get_logger, normaliser_ville, get_region, normaliser_contrat,
    MAPPING_PROFILS, TAUX_EUR_MAD, SALAIRE_MIN_MAD, SALAIRE_MAX_MAD,
    ecrire_metadata, TransformationTracker
)

logger = get_logger("silver_transform")


# ════════════════════════════════════════════════════════════════
# 1. Chargement depuis Bronze
# ════════════════════════════════════════════════════════════════

def charger_depuis_bronze(data_lake_root: str) -> pd.DataFrame:
    """Charge et consolide toutes les offres depuis la zone Bronze."""
    all_offres = []
    bronze_path = Path(data_lake_root) / 'bronze'

    for json_file in bronze_path.rglob('offres_raw.json'):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        offres = data.get('offres', [])
        all_offres.extend(offres)

    if not all_offres:
        logger.error("Aucune offre trouvée dans la zone Bronze!")
        return pd.DataFrame()

    df = pd.DataFrame(all_offres)
    logger.info(f"[SILVER] {len(df)} offres chargées depuis Bronze ({len(list(bronze_path.rglob('offres_raw.json')))} fichiers)")
    return df


# ════════════════════════════════════════════════════════════════
# 2. Normalisation des titres de poste
# ════════════════════════════════════════════════════════════════

def nettoyer_titres_postes(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """
    Standardise les intitulés de poste en familles de profils IT.
    Les titres non reconnus sont conservés avec profil 'Autre IT'.
    """
    avant = len(df)
    df['profil_source'] = df['titre_poste'].astype(str).str.lower().str.strip()
    df['profil_normalise'] = 'Autre IT'

    for pattern, profil in MAPPING_PROFILS.items():
        masque = df['profil_source'].str.contains(pattern, regex=True, na=False)
        df.loc[masque & (df['profil_normalise'] == 'Autre IT'), 'profil_normalise'] = profil

    non_classes = (df['profil_normalise'] == 'Autre IT').sum()
    classes = avant - non_classes

    if tracker:
        tracker.log("Silver — Normalisation Titres", "titre_poste",
                     "Mapping regex → profils IT normalisés",
                     avant, avant,
                     f"{classes} classés ({classes*100/avant:.1f}%), {non_classes} 'Autre IT'")

    logger.info(f"[SILVER] Titres : {classes} classés, {non_classes} 'Autre IT' sur {avant}")
    return df


# ════════════════════════════════════════════════════════════════
# 3. Normalisation des salaires
# ════════════════════════════════════════════════════════════════

def normaliser_salaires(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """
    Extrait et normalise les salaires en MAD mensuel brut.
    Gère : fourchettes, K, EUR, "Selon profil", "Confidentiel", null.
    """

    def parser_salaire(valeur):
        if pd.isna(valeur):
            return None, None, False

        s = str(valeur).strip().lower()
        if s in ['', 'null', 'confidentiel', 'selon profil', 'non précisé',
                 'à négocier', 'à discuter']:
            return None, None, False

        # Détection devise
        est_eur = 'eur' in s or '€' in s
        s = re.sub(r'(eur|€|mad|dh|dirhams?)', '', s).strip()

        # Gestion "K" (milliers)
        s = re.sub(r'(\d+(?:[.,]\d+)?)\s*k',
                   lambda m: str(int(float(m.group(1).replace(',', '.')) * 1000)), s)

        # Remplacement virgules par points
        s = s.replace(',', '.')

        # Extraction des montants
        nombres = re.findall(r'\d+(?:\.\d+)?', s)
        if not nombres:
            return None, None, False

        montants = [float(n) for n in nombres[:2]]

        # Conversion EUR → MAD
        if est_eur:
            montants = [m * TAUX_EUR_MAD for m in montants]

        if len(montants) >= 2:
            sal_min = min(montants)
            sal_max = max(montants)
        else:
            sal_min = sal_max = montants[0]

        # Validation : plage plausible pour l'IT au Maroc
        if sal_min < SALAIRE_MIN_MAD or sal_max > SALAIRE_MAX_MAD:
            return None, None, False

        return round(sal_min), round(sal_max), True

    resultats = df['salaire_brut'].apply(
        lambda x: pd.Series(parser_salaire(x),
                             index=['salaire_min_mad', 'salaire_max_mad', 'salaire_connu'])
    )
    df = pd.concat([df, resultats], axis=1)
    df['salaire_median_mad'] = df.apply(
        lambda row: round((row['salaire_min_mad'] + row['salaire_max_mad']) / 2)
        if row['salaire_connu'] else None, axis=1
    )

    nb_connu = df['salaire_connu'].sum()
    pct = nb_connu / len(df) * 100

    if tracker:
        tracker.log("Silver — Normalisation Salaires", "salaire_brut",
                     "Parsing fourchettes, K→×1000, EUR→MAD, validation plage",
                     len(df), len(df),
                     f"{nb_connu} salaires valides ({pct:.1f}%), "
                     f"{len(df)-nb_connu} non renseignés/invalides")

    logger.info(f"[SILVER] Salaires : {pct:.1f}% des offres avec salaire valide ({nb_connu}/{len(df)})")
    return df


# ════════════════════════════════════════════════════════════════
# 4. Normalisation de l'expérience
# ════════════════════════════════════════════════════════════════

def normaliser_experience(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """
    Transforme l'expérience textuelle en valeurs numériques (années).
    """

    def parser_experience(valeur):
        if pd.isna(valeur):
            return None, None

        s = str(valeur).lower().strip()

        # Cas spéciaux
        if any(mot in s for mot in ['débutant', 'junior', 'stage', 'sans expérience',
                                     'fraîchement', 'nouveau diplômé']):
            return 0, 2
        if any(mot in s for mot in ['senior', 'confirmé', 'expert', 'lead', '10+']):
            return 5, None

        # Fourchette : "3-5 ans", "3 à 5 ans"
        fourchette = re.search(r'(\d+)\s*[-àa]\s*(\d+)', s)
        if fourchette:
            return int(fourchette.group(1)), int(fourchette.group(2))

        # Minimum seul : "min 3 ans", "3+ ans", "3 ans"
        min_match = re.search(r'(?:min(?:imum)?\s*)?(\d+)\s*\+?\s*(?:ans?|years?|an)', s)
        if min_match:
            return int(min_match.group(1)), None

        return None, None

    resultats = df['experience_requise'].apply(
        lambda x: pd.Series(parser_experience(x),
                             index=['experience_min_ans', 'experience_max_ans'])
    )
    df = pd.concat([df, resultats], axis=1)

    nb_parsed = df['experience_min_ans'].notna().sum()

    if tracker:
        tracker.log("Silver — Normalisation Expérience", "experience_requise",
                     "Parsing texte libre → années min/max",
                     len(df), len(df),
                     f"{nb_parsed} valeurs parsées ({nb_parsed*100/len(df):.1f}%)")

    logger.info(f"[SILVER] Expérience : {nb_parsed}/{len(df)} parsées")
    return df


# ════════════════════════════════════════════════════════════════
# 5. Normalisation villes, contrats, dates
# ════════════════════════════════════════════════════════════════

def normaliser_villes(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """Normalise les noms de villes et ajoute la région administrative."""
    avant_uniques = df['ville'].nunique()
    df['ville_std'] = df['ville'].apply(normaliser_ville)
    df['region_admin'] = df['ville_std'].apply(get_region)
    apres_uniques = df['ville_std'].nunique()

    if tracker:
        tracker.log("Silver — Normalisation Villes", "ville",
                     "Mapping dictionnaire → noms standards + région",
                     avant_uniques, apres_uniques,
                     f"{avant_uniques} → {apres_uniques} villes uniques")

    logger.info(f"[SILVER] Villes : {avant_uniques} variantes → {apres_uniques} normalisées")
    return df


def normaliser_contrats(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """Standardise les types de contrats."""
    avant_uniques = df['type_contrat'].nunique()
    df['type_contrat_std'] = df['type_contrat'].apply(normaliser_contrat)
    apres_uniques = df['type_contrat_std'].nunique()

    if tracker:
        tracker.log("Silver — Normalisation Contrats", "type_contrat",
                     "Mapping dictionnaire → types standards",
                     avant_uniques, apres_uniques,
                     f"{avant_uniques} → {apres_uniques} types uniques")

    logger.info(f"[SILVER] Contrats : {avant_uniques} variantes → {apres_uniques} normalisés")
    return df


def nettoyer_dates(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """Nettoie et valide les dates de publication et d'expiration."""
    df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
    df['date_expiration'] = pd.to_datetime(df['date_expiration'], errors='coerce')

    # Dériver année et mois
    df['annee'] = df['date_publication'].dt.strftime('%Y')
    df['mois'] = df['date_publication'].dt.strftime('%m')

    # Détecter les incohérences (publication > expiration)
    masque_incoherent = (df['date_publication'].notna() & df['date_expiration'].notna() &
                         (df['date_publication'] > df['date_expiration']))
    nb_incoherent = masque_incoherent.sum()

    # Correction : inverser les dates incohérentes
    if nb_incoherent > 0:
        df.loc[masque_incoherent, ['date_publication', 'date_expiration']] = \
            df.loc[masque_incoherent, ['date_expiration', 'date_publication']].values
        logger.warning(f"[SILVER] {nb_incoherent} dates pub>exp corrigées par inversion")

    dates_nulles = df['date_publication'].isna().sum()

    if tracker:
        tracker.log("Silver — Nettoyage Dates", "date_publication / date_expiration",
                     "Conversion datetime, correction incohérences",
                     len(df), len(df),
                     f"{nb_incoherent} dates inversées, {dates_nulles} dates nulles")

    logger.info(f"[SILVER] Dates : {nb_incoherent} inversées, {dates_nulles} nulles")
    return df


# ════════════════════════════════════════════════════════════════
# 6. Déduplication
# ════════════════════════════════════════════════════════════════

def dedupliquer(df: pd.DataFrame, tracker: TransformationTracker = None) -> pd.DataFrame:
    """Supprime les doublons sur id_offre en gardant le premier."""
    avant = len(df)
    df = df.drop_duplicates(subset=['id_offre'], keep='first')
    apres = len(df)
    dups = avant - apres

    if tracker:
        tracker.log("Silver — Déduplication", "id_offre",
                     "drop_duplicates sur id_offre",
                     avant, apres,
                     f"{dups} doublons supprimés")

    if dups > 0:
        logger.warning(f"[SILVER] {dups} doublons supprimés")
    return df


# ════════════════════════════════════════════════════════════════
# 7. Pipeline Silver complet
# ════════════════════════════════════════════════════════════════

def transformer_silver(data_lake_root: str,
                       tracker: TransformationTracker = None) -> pd.DataFrame:
    """
    Orchestre toutes les transformations Bronze → Silver.
    Retourne le DataFrame nettoyé.
    """
    logger.info("=" * 60)
    logger.info("DÉBUT PIPELINE SILVER")
    logger.info("=" * 60)

    # Chargement
    df = charger_depuis_bronze(data_lake_root)
    if df.empty:
        return df

    # Transformations séquentielles
    df = dedupliquer(df, tracker)
    df = normaliser_villes(df, tracker)
    df = nettoyer_titres_postes(df, tracker)
    df = normaliser_salaires(df, tracker)
    df = normaliser_experience(df, tracker)
    df = normaliser_contrats(df, tracker)
    df = nettoyer_dates(df, tracker)

    logger.info("=" * 60)
    logger.info(f"PIPELINE SILVER TERMINÉ — {len(df)} offres nettoyées")
    logger.info("=" * 60)

    return df
