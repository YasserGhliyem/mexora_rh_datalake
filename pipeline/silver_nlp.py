"""
silver_nlp.py — Extraction de compétences IT depuis texte libre.

C'est la transformation la plus importante du projet : elle transforme
du texte non structuré (descriptions, compétences brutes) en données
structurées exploitables analytiquement.

Stratégie :
  1. Chargement du référentiel de compétences IT (300 compétences, aliases)
  2. Concaténation description + competences_brut
  3. Matching par word boundaries (regex) sur les aliases
  4. Résolution vers le nom normalisé + famille
"""

import pandas as pd
import re
import json
from pathlib import Path

from pipeline.utils import get_logger, ecrire_metadata, TransformationTracker

logger = get_logger("silver_nlp")


def charger_referentiel(referentiel_path: str) -> dict:
    """
    Charge le référentiel et construit un dictionnaire plat
    alias → {competence, famille}, trié par longueur décroissante
    pour éviter les faux positifs (ex: "node" ne matche pas avant "node.js").
    """
    with open(referentiel_path, 'r', encoding='utf-8') as f:
        referentiel = json.load(f)

    dict_competences = {}
    nb_aliases = 0

    for famille, competences in referentiel['familles'].items():
        for nom_normalise, aliases in competences.items():
            for alias in aliases:
                dict_competences[alias.lower().strip()] = {
                    'competence': nom_normalise,
                    'famille': famille
                }
                nb_aliases += 1

    logger.info(f"[NLP] Référentiel chargé : {nb_aliases} aliases → "
                f"{len(set(v['competence'] for v in dict_competences.values()))} compétences, "
                f"{len(set(v['famille'] for v in dict_competences.values()))} familles")

    return dict_competences


def extraire_competences(df: pd.DataFrame, referentiel_path: str,
                         tracker: TransformationTracker = None) -> pd.DataFrame:
    """
    Extrait les compétences IT depuis deux sources :
      1. Le champ 'competences_brut' (liste semi-structurée)
      2. Le champ 'description' (texte libre — plus riche mais plus bruité)

    Chaque offre produit une ligne par compétence détectée.

    Args:
        df: DataFrame des offres Silver (nettoyées)
        referentiel_path: Chemin vers referentiel_competences_it.json
        tracker: Objet de suivi des transformations

    Returns:
        DataFrame avec une ligne par (offre, compétence) détectée
    """
    logger.info("=" * 60)
    logger.info("DÉBUT EXTRACTION COMPÉTENCES (NLP)")
    logger.info("=" * 60)

    dict_competences = charger_referentiel(referentiel_path)

    # Trier par longueur décroissante pour priorité aux termes longs
    aliases_tries = sorted(dict_competences.keys(), key=len, reverse=True)

    # Pré-compiler les regex pour performance
    patterns_compiles = {}
    for alias in aliases_tries:
        try:
            patterns_compiles[alias] = re.compile(r'\b' + re.escape(alias) + r'\b', re.IGNORECASE)
        except re.error:
            logger.warning(f"Regex invalide pour alias: {alias}")
            continue

    resultats = []
    offres_sans_competence = 0
    total_competences = 0

    for idx, offre in df.iterrows():
        # Concaténer les deux sources de texte
        texte_brut = str(offre.get('competences_brut', '') or '')
        texte_desc = str(offre.get('description', '') or '')

        # Normaliser les séparateurs courants
        for sep in ['•', '/', '|', ';', '\n', '\r', '–', '—']:
            texte_brut = texte_brut.replace(sep, ', ')

        texte_complet = f"{texte_brut} {texte_desc}".lower()

        competences_trouvees = set()

        for alias, pattern in patterns_compiles.items():
            if pattern.search(texte_complet):
                info = dict_competences[alias]
                cle = info['competence']
                if cle not in competences_trouvees:
                    competences_trouvees.add(cle)
                    resultats.append({
                        'id_offre':   offre.get('id_offre'),
                        'profil':     offre.get('profil_normalise', 'Autre IT'),
                        'ville':      offre.get('ville_std', 'Inconnue'),
                        'competence': info['competence'],
                        'famille':    info['famille'],
                        'date_pub':   str(offre.get('date_publication', '')),
                        'annee':      str(offre.get('annee', '')),
                        'mois':       str(offre.get('mois', '')),
                    })

        if competences_trouvees:
            total_competences += len(competences_trouvees)
        else:
            offres_sans_competence += 1
            resultats.append({
                'id_offre':   offre.get('id_offre'),
                'profil':     offre.get('profil_normalise', 'Autre IT'),
                'ville':      offre.get('ville_std', 'Inconnue'),
                'competence': 'non_détecté',
                'famille':    'inconnu',
                'date_pub':   str(offre.get('date_publication', '')),
                'annee':      str(offre.get('annee', '')),
                'mois':       str(offre.get('mois', '')),
            })

        # Log de progression
        if (idx + 1) % 1000 == 0:
            logger.info(f"  ├─ {idx+1}/{len(df)} offres traitées...")

    df_competences = pd.DataFrame(resultats)

    nb_offres_avec = len(df) - offres_sans_competence
    moy_comp = total_competences / nb_offres_avec if nb_offres_avec > 0 else 0

    if tracker:
        tracker.log("Silver NLP — Extraction Compétences",
                     "description + competences_brut",
                     "Matching regex word-boundary sur référentiel IT",
                     len(df), len(df_competences),
                     f"{nb_offres_avec}/{len(df)} offres avec compétences, "
                     f"{total_competences} détections totales, "
                     f"moy {moy_comp:.1f}/offre, "
                     f"{offres_sans_competence} sans compétence")

    logger.info("=" * 60)
    logger.info(f"[NLP] ✅ {len(df_competences)} lignes compétences extraites")
    logger.info(f"[NLP]    {nb_offres_avec}/{len(df)} offres avec au moins 1 compétence")
    logger.info(f"[NLP]    Moyenne : {moy_comp:.1f} compétences/offre")
    logger.info(f"[NLP]    {offres_sans_competence} offres sans compétence détectée")
    logger.info("=" * 60)

    return df_competences


def sauvegarder_silver(df_offres: pd.DataFrame, df_competences: pd.DataFrame,
                       data_lake_root: str):
    """Sauvegarde les données Silver au format Parquet compressé Snappy."""
    silver_path = Path(data_lake_root) / 'silver'

    # ── Offres nettoyées ──────────────────────────────────────────
    chemin_offres = silver_path / 'offres_clean' / 'offres_clean.parquet'
    chemin_offres.parent.mkdir(parents=True, exist_ok=True)

    # Conversion des colonnes datetime pour Parquet
    for col in ['date_publication', 'date_expiration']:
        if col in df_offres.columns:
            df_offres[col] = pd.to_datetime(df_offres[col], errors='coerce')

    df_offres.to_parquet(chemin_offres, index=False, compression='snappy')
    taille_offres = chemin_offres.stat().st_size / 1024
    logger.info(f"[SILVER] offres_clean.parquet → {taille_offres:.0f} Ko ({len(df_offres)} lignes)")

    # Metadata
    ecrire_metadata(str(chemin_offres.parent), {
        'table': 'offres_clean',
        'format': 'Parquet (Snappy)',
        'nb_lignes': len(df_offres),
        'colonnes': list(df_offres.columns),
        'taille_ko': round(taille_offres),
    })

    # ── Compétences extraites ─────────────────────────────────────
    chemin_comp = silver_path / 'competences_extraites' / 'competences.parquet'
    chemin_comp.parent.mkdir(parents=True, exist_ok=True)
    df_competences.to_parquet(chemin_comp, index=False, compression='snappy')
    taille_comp = chemin_comp.stat().st_size / 1024
    logger.info(f"[SILVER] competences.parquet → {taille_comp:.0f} Ko ({len(df_competences)} lignes)")

    # Metadata
    ecrire_metadata(str(chemin_comp.parent), {
        'table': 'competences_extraites',
        'format': 'Parquet (Snappy)',
        'nb_lignes': len(df_competences),
        'colonnes': list(df_competences.columns),
        'taille_ko': round(taille_comp),
    })

    logger.info(f"[SILVER] ✅ Zone Silver sauvegardée ({taille_offres + taille_comp:.0f} Ko total)")
