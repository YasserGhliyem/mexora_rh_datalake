"""
main.py — Orchestrateur du pipeline Mexora RH Data Lake.

Exécute séquentiellement les 3 étapes du pipeline :
  1. BRONZE : Ingestion brute (JSON partitionné par source/mois)
  2. SILVER : Nettoyage + Extraction NLP des compétences (→ Parquet)
  3. GOLD   : Agrégation analytique via DuckDB (→ 5 tables Parquet)

Usage :
  python main.py
  python main.py --source chemin/vers/offres.json
  python main.py --etape silver   (reprendre à partir de Silver)
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_LAKE_ROOT = str(BASE_DIR / 'data_lake_mexora_rh')

# Fichiers source
SOURCE_OFFRES = str(BASE_DIR / 'offres_emploi_it_maroc.json')
SOURCE_REFERENTIEL = str(BASE_DIR / 'referentiel_competences_it.json')
SOURCE_ENTREPRISES = str(BASE_DIR / 'entreprises_it_maroc.csv')

# Rapport de sortie
RAPPORT_SORTIE = str(BASE_DIR / 'rapport_pipeline.md')


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Mexora RH — Data Lake IT Maroc"
    )
    parser.add_argument('--source', default=SOURCE_OFFRES,
                        help='Chemin vers le fichier JSON des offres')
    parser.add_argument('--datalake', default=DATA_LAKE_ROOT,
                        help='Racine du Data Lake')
    parser.add_argument('--referentiel', default=SOURCE_REFERENTIEL,
                        help='Chemin vers le référentiel de compétences')
    parser.add_argument('--etape', choices=['bronze', 'silver', 'gold', 'all'],
                        default='all',
                        help='Étape à exécuter (default: all)')
    args = parser.parse_args()

    # ── Imports pipeline ──────────────────────────────────────────
    from pipeline.utils import get_logger, TransformationTracker
    from pipeline.bronze_ingestion import ingerer_bronze, copier_referentiels
    from pipeline.silver_transform import transformer_silver
    from pipeline.silver_nlp import extraire_competences, sauvegarder_silver
    from pipeline.gold_aggregation import construire_gold

    logger = get_logger("main")
    tracker = TransformationTracker()

    start_total = time.time()

    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║      PIPELINE MEXORA RH — DATA LAKE IT MAROC         ║")
    logger.info("╠════════════════════════════════════════════════════════╣")
    logger.info(f"║  Date       : {datetime.now():%Y-%m-%d %H:%M:%S}                  ║")
    logger.info(f"║  Étape      : {args.etape:<40s} ║")
    logger.info(f"║  Data Lake  : {os.path.basename(args.datalake):<40s} ║")
    logger.info("╚════════════════════════════════════════════════════════╝")

    # ══════════════════════════════════════════════════════════════
    # ÉTAPE 1 — BRONZE : Ingestion brute
    # ══════════════════════════════════════════════════════════════
    if args.etape in ('all', 'bronze'):
        logger.info("\n" + "▓" * 60)
        logger.info("▓  ÉTAPE 1/3 — BRONZE : Ingestion brute")
        logger.info("▓" * 60)

        start = time.time()

        if not os.path.exists(args.source):
            logger.error(f"Fichier source introuvable : {args.source}")
            logger.error("Exécutez d'abord : python data_generator_p2.py")
            sys.exit(1)

        stats_bronze = ingerer_bronze(args.source, args.datalake, tracker)

        # Copier les référentiels
        copier_referentiels(args.referentiel, SOURCE_ENTREPRISES, args.datalake)

        elapsed = time.time() - start
        logger.info(f"[BRONZE] Terminé en {elapsed:.1f}s")

    # ══════════════════════════════════════════════════════════════
    # ÉTAPE 2 — SILVER : Nettoyage + NLP
    # ══════════════════════════════════════════════════════════════
    if args.etape in ('all', 'silver'):
        logger.info("\n" + "▓" * 60)
        logger.info("▓  ÉTAPE 2/3 — SILVER : Nettoyage & Extraction NLP")
        logger.info("▓" * 60)

        start = time.time()

        # 2a. Nettoyage et standardisation
        df_offres = transformer_silver(args.datalake, tracker)

        if df_offres.empty:
            logger.error("Aucune offre après transformation Silver. Arrêt.")
            sys.exit(1)

        # 2b. Extraction des compétences (NLP)
        if not os.path.exists(args.referentiel):
            logger.error(f"Référentiel introuvable : {args.referentiel}")
            sys.exit(1)

        df_competences = extraire_competences(df_offres, args.referentiel, tracker)

        # 2c. Sauvegarde en Parquet
        sauvegarder_silver(df_offres, df_competences, args.datalake)

        elapsed = time.time() - start
        logger.info(f"[SILVER] Terminé en {elapsed:.1f}s")

    # ══════════════════════════════════════════════════════════════
    # ÉTAPE 3 — GOLD : Agrégation analytique
    # ══════════════════════════════════════════════════════════════
    if args.etape in ('all', 'gold'):
        logger.info("\n" + "▓" * 60)
        logger.info("▓  ÉTAPE 3/3 — GOLD : Agrégation analytique (DuckDB)")
        logger.info("▓" * 60)

        start = time.time()
        construire_gold(args.datalake, tracker)
        elapsed = time.time() - start
        logger.info(f"[GOLD] Terminé en {elapsed:.1f}s")

    # ══════════════════════════════════════════════════════════════
    # RAPPORT FINAL
    # ══════════════════════════════════════════════════════════════
    total_elapsed = time.time() - start_total

    logger.info("\n" + "═" * 60)
    logger.info(f"PIPELINE TERMINÉ en {total_elapsed:.1f}s")
    logger.info("═" * 60)

    # Générer le rapport de transformations
    rapport_path = tracker.generer_rapport(RAPPORT_SORTIE)
    logger.info(f"Rapport sauvegardé : {rapport_path}")

    # Résumé du Data Lake
    datalake_path = Path(args.datalake)
    logger.info("\n📊 Résumé du Data Lake :")

    for zone in ['bronze', 'silver', 'gold']:
        zone_path = datalake_path / zone
        if zone_path.exists():
            fichiers = list(zone_path.rglob('*'))
            fichiers_data = [f for f in fichiers if f.suffix in ('.json', '.parquet')]
            taille = sum(f.stat().st_size for f in fichiers_data if f.is_file()) / 1024
            logger.info(f"  ├─ {zone.upper():6s} : {len(fichiers_data):3d} fichiers ({taille:.0f} Ko)")

    logger.info(f"\n✅ Tous les livrables sont dans : {args.datalake}")


if __name__ == '__main__':
    main()
