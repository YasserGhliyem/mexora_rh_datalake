"""
bronze_ingestion.py — Chargement brut dans la zone Bronze.

Principe fondamental : la zone Bronze est IMMUABLE.
On ne modifie JAMAIS les données une fois chargées en Bronze.
C'est l'archive fidèle de ce qui a été reçu.

Partitionnement : par source (rekrute, marocannonce, linkedin) et par mois.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from pipeline.utils import get_logger, ecrire_metadata, TransformationTracker

logger = get_logger("bronze_ingestion")


def ingerer_bronze(filepath_source: str, data_lake_root: str,
                   tracker: TransformationTracker = None) -> dict:
    """
    Charge les données brutes dans la zone Bronze sans aucune modification.
    Partitionne par source et par mois de publication.

    Args:
        filepath_source: Chemin vers le fichier JSON source (offres_emploi_it_maroc.json)
        data_lake_root: Racine du Data Lake (data_lake_mexora_rh/)
        tracker: Objet de suivi des transformations

    Returns:
        dict: Statistiques d'ingestion (total, par_source, par_mois, nb_fichiers)
    """
    logger.info(f"Début ingestion Bronze depuis : {filepath_source}")

    # ── Lecture du fichier source ──────────────────────────────────────
    with open(filepath_source, 'r', encoding='utf-8') as f:
        data = json.load(f)

    offres = data.get('offres', data) if isinstance(data, dict) else data
    if isinstance(offres, dict):
        offres = [offres]

    total = len(offres)
    logger.info(f"{total} offres lues depuis le fichier source")

    stats = {
        'total': total,
        'par_source': {},
        'par_mois': {},
        'nb_fichiers': 0
    }

    # ── Partitionnement par source et par mois ────────────────────────
    partitions = {}
    erreurs_date = 0

    for offre in offres:
        source = offre.get('source', 'inconnu').lower().replace(' ', '_')
        date_pub = offre.get('date_publication', '')

        try:
            mois_partition = datetime.strptime(str(date_pub)[:7], '%Y-%m').strftime('%Y_%m')
        except (ValueError, TypeError):
            mois_partition = 'date_inconnue'
            erreurs_date += 1

        cle = f"{source}/{mois_partition}"
        if cle not in partitions:
            partitions[cle] = []
        partitions[cle].append(offre)

        # Stats
        stats['par_source'][source] = stats['par_source'].get(source, 0) + 1
        stats['par_mois'][mois_partition] = stats['par_mois'].get(mois_partition, 0) + 1

    if erreurs_date > 0:
        logger.warning(f"{erreurs_date} offres avec date_publication invalide → partition 'date_inconnue'")

    # ── Écriture dans Bronze ──────────────────────────────────────────
    nb_fichiers = 0
    for partition, offres_partition in partitions.items():
        chemin_dir = os.path.join(data_lake_root, 'bronze', partition)
        os.makedirs(chemin_dir, exist_ok=True)

        chemin_fichier = os.path.join(chemin_dir, 'offres_raw.json')
        with open(chemin_fichier, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source_fichier': os.path.basename(filepath_source),
                    'date_ingestion': datetime.now().isoformat(),
                    'partition': partition,
                    'nb_offres': len(offres_partition),
                    'pipeline_version': '2.0'
                },
                'offres': offres_partition
            }, f, ensure_ascii=False, indent=2)

        nb_fichiers += 1

    stats['nb_fichiers'] = nb_fichiers

    # ── Metadata de la zone Bronze ────────────────────────────────────
    bronze_path = os.path.join(data_lake_root, 'bronze')
    ecrire_metadata(bronze_path, {
        'zone': 'bronze',
        'description': 'Données brutes des offres d\'emploi IT Maroc — archive immuable',
        'format': 'JSON',
        'partitionnement': 'source / mois',
        'nb_offres_total': total,
        'nb_partitions': nb_fichiers,
        'sources': list(stats['par_source'].keys()),
        'source_fichier': os.path.basename(filepath_source),
    })

    # ── Tracking ──────────────────────────────────────────────────────
    if tracker:
        tracker.log(
            etape="Bronze — Ingestion",
            champ="offres_raw",
            regle="Partitionnement par source et par mois, sans transformation",
            avant=total,
            apres=total,
            details=f"{nb_fichiers} partitions créées, "
                    f"{len(stats['par_source'])} sources, "
                    f"{erreurs_date} dates invalides"
        )

    logger.info(f"[BRONZE] ✅ {total} offres ingérées dans {nb_fichiers} partitions")
    for source, count in stats['par_source'].items():
        logger.info(f"  └─ {source}: {count} offres")

    return stats


def copier_referentiels(referentiel_path: str, entreprises_path: str,
                        data_lake_root: str):
    """
    Copie les fichiers complémentaires (référentiel compétences, entreprises)
    dans la zone Bronze pour traçabilité.
    """
    import shutil

    ref_dest = os.path.join(data_lake_root, 'bronze', '_referentiels')
    os.makedirs(ref_dest, exist_ok=True)

    if os.path.exists(referentiel_path):
        shutil.copy2(referentiel_path, os.path.join(ref_dest, 'referentiel_competences_it.json'))
        logger.info(f"[BRONZE] Référentiel compétences copié dans Bronze")

    if os.path.exists(entreprises_path):
        shutil.copy2(entreprises_path, os.path.join(ref_dest, 'entreprises_it_maroc.csv'))
        logger.info(f"[BRONZE] Fichier entreprises copié dans Bronze")

    ecrire_metadata(ref_dest, {
        'description': 'Fichiers de référence copiés pour traçabilité',
        'fichiers': ['referentiel_competences_it.json', 'entreprises_it_maroc.csv']
    })
