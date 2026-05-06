"""
gold_aggregation.py — Construction des tables Gold depuis Silver.

Utilise DuckDB pour exécuter des requêtes SQL analytiques directement
sur les fichiers Parquet de la zone Silver.

Tables Gold produites :
  1. top_competences.parquet      — Top compétences par profil IT
  2. salaires_par_profil.parquet  — Statistiques salariales par profil et ville
  3. offres_par_ville.parquet     — Volume d'offres par ville et profil
  4. entreprises_recruteurs.parquet — Top entreprises qui recrutent
  5. tendances_mensuelles.parquet — Évolution mensuelle des offres
"""

import duckdb
from pathlib import Path

from pipeline.utils import get_logger, ecrire_metadata, TransformationTracker

logger = get_logger("gold_aggregation")


def construire_gold(data_lake_root: str,
                    tracker: TransformationTracker = None):
    """
    Construit toutes les tables Gold depuis les données Silver.
    Utilise DuckDB pour les requêtes SQL directement sur les fichiers Parquet.
    """
    silver_offres = str(Path(data_lake_root) / 'silver' / 'offres_clean' / 'offres_clean.parquet')
    silver_comp = str(Path(data_lake_root) / 'silver' / 'competences_extraites' / 'competences.parquet')
    gold_path = Path(data_lake_root) / 'gold'
    gold_path.mkdir(parents=True, exist_ok=True)

    # Normaliser les chemins pour DuckDB (forward slashes)
    silver_offres = silver_offres.replace('\\', '/')
    silver_comp = silver_comp.replace('\\', '/')

    con = duckdb.connect()

    logger.info("=" * 60)
    logger.info("DÉBUT CONSTRUCTION TABLES GOLD")
    logger.info("=" * 60)

    # ── Table Gold 1 : Top compétences par profil ──────────────────
    logger.info("[GOLD] 1/5 — Construction top_competences...")
    try:
        df_top_comp = con.execute(f"""
            SELECT
                profil,
                famille,
                competence,
                COUNT(DISTINCT id_offre)  AS nb_offres_mentionnent,
                ROUND(COUNT(DISTINCT id_offre) * 100.0 /
                    (SELECT COUNT(DISTINCT id_offre) FROM read_parquet('{silver_comp}')), 2)
                    AS pct_offres_total,
                RANK() OVER (
                    PARTITION BY profil
                    ORDER BY COUNT(DISTINCT id_offre) DESC
                ) AS rang_dans_profil
            FROM read_parquet('{silver_comp}')
            WHERE competence != 'non_détecté'
            GROUP BY profil, famille, competence
            ORDER BY profil, rang_dans_profil
        """).df()

        chemin = gold_path / 'top_competences.parquet'
        df_top_comp.to_parquet(chemin, index=False, compression='snappy')
        logger.info(f"  └─ {len(df_top_comp)} lignes → top_competences.parquet")

        if tracker:
            tracker.log("Gold — Top Compétences", "top_competences",
                         "Agrégation compétences par profil avec ranking",
                         0, len(df_top_comp),
                         f"{df_top_comp['competence'].nunique()} compétences uniques")
    except Exception as e:
        logger.error(f"  └─ ERREUR top_competences : {e}")

    # ── Table Gold 2 : Salaires par profil et ville ────────────────
    logger.info("[GOLD] 2/5 — Construction salaires_par_profil...")
    try:
        df_salaires = con.execute(f"""
            SELECT
                profil_normalise        AS profil,
                ville_std               AS ville,
                type_contrat_std        AS type_contrat,
                COUNT(*)                AS nb_offres,
                COUNT(*) FILTER (WHERE salaire_connu = true)
                                        AS nb_offres_avec_salaire,
                ROUND(MEDIAN(salaire_median_mad) FILTER (WHERE salaire_connu = true), 0)
                                        AS salaire_median_mad,
                ROUND(AVG(salaire_median_mad) FILTER (WHERE salaire_connu = true), 0)
                                        AS salaire_moyen_mad,
                ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP
                    (ORDER BY salaire_median_mad) FILTER (WHERE salaire_connu = true), 0)
                                        AS salaire_q1_mad,
                ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP
                    (ORDER BY salaire_median_mad) FILTER (WHERE salaire_connu = true), 0)
                                        AS salaire_q3_mad,
                ROUND(MIN(salaire_min_mad) FILTER (WHERE salaire_connu = true), 0)
                                        AS salaire_min_observe,
                ROUND(MAX(salaire_max_mad) FILTER (WHERE salaire_connu = true), 0)
                                        AS salaire_max_observe
            FROM read_parquet('{silver_offres}')
            GROUP BY profil_normalise, ville_std, type_contrat_std
            HAVING COUNT(*) >= 3
            ORDER BY nb_offres DESC
        """).df()

        chemin = gold_path / 'salaires_par_profil.parquet'
        df_salaires.to_parquet(chemin, index=False, compression='snappy')
        logger.info(f"  └─ {len(df_salaires)} lignes → salaires_par_profil.parquet")

        if tracker:
            tracker.log("Gold — Salaires par Profil", "salaires_par_profil",
                         "Statistiques salariales (médiane, Q1, Q3, min, max) par profil/ville",
                         0, len(df_salaires),
                         f"{df_salaires['profil'].nunique()} profils, {df_salaires['ville'].nunique()} villes")
    except Exception as e:
        logger.error(f"  └─ ERREUR salaires_par_profil : {e}")

    # ── Table Gold 3 : Offres par ville ────────────────────────────
    logger.info("[GOLD] 3/5 — Construction offres_par_ville...")
    try:
        df_villes = con.execute(f"""
            SELECT
                ville_std               AS ville,
                region_admin,
                profil_normalise        AS profil,
                annee,
                mois,
                COUNT(*)                AS nb_offres,
                COUNT(*) FILTER (WHERE
                    teletravail ILIKE '%télétravail%'
                    OR teletravail ILIKE '%remote%'
                    OR teletravail ILIKE '%hybride%')
                                        AS nb_offres_remote,
                ROUND(COUNT(*) FILTER (WHERE
                    teletravail ILIKE '%télétravail%'
                    OR teletravail ILIKE '%remote%'
                    OR teletravail ILIKE '%hybride%') * 100.0
                    / NULLIF(COUNT(*), 0), 1)
                                        AS pct_remote
            FROM read_parquet('{silver_offres}')
            GROUP BY ville_std, region_admin, profil_normalise, annee, mois
            ORDER BY nb_offres DESC
        """).df()

        chemin = gold_path / 'offres_par_ville.parquet'
        df_villes.to_parquet(chemin, index=False, compression='snappy')
        logger.info(f"  └─ {len(df_villes)} lignes → offres_par_ville.parquet")

        if tracker:
            tracker.log("Gold — Offres par Ville", "offres_par_ville",
                         "Volume d'offres par ville/profil/mois avec taux télétravail",
                         0, len(df_villes),
                         f"{df_villes['ville'].nunique()} villes, pct_remote moyen: {df_villes['pct_remote'].mean():.1f}%")
    except Exception as e:
        logger.error(f"  └─ ERREUR offres_par_ville : {e}")

    # ── Table Gold 4 : Top entreprises ─────────────────────────────
    logger.info("[GOLD] 4/5 — Construction entreprises_recruteurs...")
    try:
        df_entreprises = con.execute(f"""
            SELECT
                entreprise,
                ville_std                               AS ville,
                COUNT(*)                                AS nb_offres_publiees,
                COUNT(DISTINCT profil_normalise)        AS nb_profils_differents,
                ROUND(AVG(salaire_median_mad) FILTER (WHERE salaire_connu = true), 0)
                                                        AS salaire_moyen_propose,
                LIST(DISTINCT profil_normalise ORDER BY profil_normalise)
                                                        AS profils_recrutes,
                MIN(CAST(date_publication AS VARCHAR))  AS premiere_offre,
                MAX(CAST(date_publication AS VARCHAR))  AS derniere_offre
            FROM read_parquet('{silver_offres}')
            WHERE entreprise IS NOT NULL
              AND entreprise != ''
            GROUP BY entreprise, ville_std
            HAVING COUNT(*) >= 2
            ORDER BY nb_offres_publiees DESC
            LIMIT 100
        """).df()

        chemin = gold_path / 'entreprises_recruteurs.parquet'
        df_entreprises.to_parquet(chemin, index=False, compression='snappy')
        logger.info(f"  └─ {len(df_entreprises)} lignes → entreprises_recruteurs.parquet")

        if tracker:
            tracker.log("Gold — Top Entreprises", "entreprises_recruteurs",
                         "Top 100 entreprises par volume d'offres (min 2)",
                         0, len(df_entreprises),
                         f"{len(df_entreprises)} entreprises, "
                         f"max offres: {df_entreprises['nb_offres_publiees'].max() if len(df_entreprises) > 0 else 0}")
    except Exception as e:
        logger.error(f"  └─ ERREUR entreprises_recruteurs : {e}")

    # ── Table Gold 5 : Tendances mensuelles ────────────────────────
    logger.info("[GOLD] 5/5 — Construction tendances_mensuelles...")
    try:
        df_tendances = con.execute(f"""
            SELECT
                annee,
                mois,
                profil_normalise                        AS profil,
                COUNT(*)                                AS nb_offres,
                ROUND(AVG(salaire_median_mad) FILTER (WHERE salaire_connu = true), 0)
                                                        AS salaire_moyen_mois,
                LAG(COUNT(*)) OVER (
                    PARTITION BY profil_normalise
                    ORDER BY annee, mois
                )                                       AS nb_offres_mois_precedent
            FROM read_parquet('{silver_offres}')
            WHERE annee IS NOT NULL
            GROUP BY annee, mois, profil_normalise
            ORDER BY profil_normalise, annee, mois
        """).df()

        # Calcul de l'évolution en pourcentage
        df_tendances['evolution_pct'] = (
            (df_tendances['nb_offres'] - df_tendances['nb_offres_mois_precedent'])
            / df_tendances['nb_offres_mois_precedent'] * 100
        ).round(1)

        chemin = gold_path / 'tendances_mensuelles.parquet'
        df_tendances.to_parquet(chemin, index=False, compression='snappy')
        logger.info(f"  └─ {len(df_tendances)} lignes → tendances_mensuelles.parquet")

        if tracker:
            tracker.log("Gold — Tendances Mensuelles", "tendances_mensuelles",
                         "Évolution mensuelle des offres par profil avec LAG",
                         0, len(df_tendances),
                         f"{df_tendances['annee'].nunique()} années, "
                         f"{df_tendances['profil'].nunique()} profils")
    except Exception as e:
        logger.error(f"  └─ ERREUR tendances_mensuelles : {e}")

    # ── Metadata Gold ─────────────────────────────────────────────
    tables_gold = list(gold_path.glob('*.parquet'))
    ecrire_metadata(str(gold_path), {
        'zone': 'gold',
        'description': 'Tables analytiques pré-calculées pour dashboards et reporting',
        'format': 'Parquet (Snappy)',
        'nb_tables': len(tables_gold),
        'tables': [t.name for t in tables_gold],
        'source': 'Zone Silver (offres_clean + competences)',
        'outil_requetage': 'DuckDB SQL',
    })

    con.close()

    logger.info("=" * 60)
    logger.info(f"[GOLD] ✅ {len(tables_gold)} tables Gold construites")
    logger.info("=" * 60)
