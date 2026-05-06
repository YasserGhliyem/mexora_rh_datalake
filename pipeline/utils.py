"""
utils.py — Fonctions partagées du pipeline Mexora RH.

Centralise les constantes, mappings et helpers utilisés
par les différentes étapes du pipeline (Bronze, Silver, Gold).
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path

# ════════════════════════════════════════════════════════════════
# Configuration du logger
# ════════════════════════════════════════════════════════════════

def get_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """Crée un logger avec sortie console + fichier."""
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(
            "%(asctime)s │ %(name)-18s │ %(levelname)-7s │ %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(ch)

        # File handler
        fh = logging.FileHandler(
            os.path.join(log_dir, f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"),
            encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s"
        ))
        logger.addHandler(fh)

    return logger


# ════════════════════════════════════════════════════════════════
# Constantes métier
# ════════════════════════════════════════════════════════════════

TAUX_EUR_MAD = 10.8  # Taux de conversion EUR → MAD (2024)

SALAIRE_MIN_MAD = 3_000    # Salaire minimum plausible (IT Maroc)
SALAIRE_MAX_MAD = 100_000  # Salaire maximum plausible (IT Maroc)

# ════════════════════════════════════════════════════════════════
# Mapping de normalisation des villes
# ════════════════════════════════════════════════════════════════

MAPPING_VILLES = {
    # Casablanca
    "casa": "Casablanca", "casablanca": "Casablanca", "CASABLANCA": "Casablanca",
    "Casa": "Casablanca", "CASA": "Casablanca", "casa blanca": "Casablanca",
    "Dar el Beida": "Casablanca", "CasaBlanca": "Casablanca",
    # Rabat
    "rabat": "Rabat", "RABAT": "Rabat", "Rabat-Salé": "Rabat",
    "rabat sale": "Rabat", "Rbt": "Rabat",
    # Marrakech
    "marrakech": "Marrakech", "MARRAKECH": "Marrakech",
    "Marrakesh": "Marrakech", "marrakesh": "Marrakech", "MRK": "Marrakech",
    # Tanger
    "tanger": "Tanger", "TANGER": "Tanger", "Tangier": "Tanger",
    "tangier": "Tanger", "Tanja": "Tanger", "TNG": "Tanger",
    # Fès
    "fes": "Fès", "FES": "Fès", "Fes": "Fès", "fès": "Fès", "Fez": "Fès",
    # Agadir
    "agadir": "Agadir", "AGADIR": "Agadir",
    # Oujda
    "oujda": "Oujda", "OUJDA": "Oujda",
    # Kénitra
    "kenitra": "Kénitra", "KENITRA": "Kénitra", "Kenitra": "Kénitra",
    # Tétouan
    "tetouan": "Tétouan", "TETOUAN": "Tétouan", "Tetouan": "Tétouan",
    # Meknès
    "meknes": "Meknès", "MEKNES": "Meknès", "Meknes": "Meknès",
    # Mohammedia
    "mohammedia": "Mohammedia", "MOHAMMEDIA": "Mohammedia",
    # El Jadida
    "el jadida": "El Jadida", "EL JADIDA": "El Jadida",
    # Salé
    "sale": "Salé", "SALE": "Salé", "Sale": "Salé",
    # Settat
    "settat": "Settat", "SETTAT": "Settat",
    # Beni Mellal
    "beni mellal": "Beni Mellal", "BENI MELLAL": "Beni Mellal",
}

# ════════════════════════════════════════════════════════════════
# Mapping des régions administratives
# ════════════════════════════════════════════════════════════════

MAPPING_REGIONS = {
    "Casablanca": "Casablanca-Settat",
    "Mohammedia": "Casablanca-Settat",
    "El Jadida": "Casablanca-Settat",
    "Settat": "Casablanca-Settat",
    "Rabat": "Rabat-Salé-Kénitra",
    "Salé": "Rabat-Salé-Kénitra",
    "Kénitra": "Rabat-Salé-Kénitra",
    "Marrakech": "Marrakech-Safi",
    "Fès": "Fès-Meknès",
    "Meknès": "Fès-Meknès",
    "Tanger": "Tanger-Tétouan-Al Hoceïma",
    "Tétouan": "Tanger-Tétouan-Al Hoceïma",
    "Agadir": "Souss-Massa",
    "Oujda": "Oriental",
    "Beni Mellal": "Béni Mellal-Khénifra",
}

# ════════════════════════════════════════════════════════════════
# Mapping de normalisation des types de contrats
# ════════════════════════════════════════════════════════════════

MAPPING_CONTRATS = {
    "cdi": "CDI", "CDI": "CDI", "Cdi": "CDI",
    "contrat à durée indéterminée": "CDI", "permanent": "CDI",
    "cdd": "CDD", "CDD": "CDD", "Cdd": "CDD",
    "contrat à durée déterminée": "CDD", "temporaire": "CDD",
    "stage": "Stage", "STAGE": "Stage", "internship": "Stage",
    "freelance": "Freelance", "FREELANCE": "Freelance",
    "indépendant": "Freelance", "consultant": "Freelance",
    "interim": "Intérim", "intérim": "Intérim",
    "anapec": "ANAPEC", "contrat anapec": "ANAPEC",
}

# ════════════════════════════════════════════════════════════════
# Mapping de normalisation des profils IT
# ════════════════════════════════════════════════════════════════

MAPPING_PROFILS = {
    # Data Engineering
    r'data\s*eng(ineer|ineer\w*|\.)?|ingénieur\s+data|dev\s+data\s+eng': 'Data Engineer',
    r'etl\s*dev|pipeline\s*dev|ingénieur\s+etl': 'Data Engineer',

    # Data Analysis / BI
    r'data\s*anal(yst|yste|ytics)|analyste?\s+data|bi\s+anal': 'Data Analyst',
    r'business\s+intel(ligence)?|ingénieur\s+bi|développeur\s+bi': 'Data Analyst',
    r'reporting\s+(anal|spec|officer)': 'Data Analyst',

    # Data Science / ML
    r'data\s*sci(entist|ence)|machine\s*learn|ml\s*eng|ia\s*eng': 'Data Scientist',
    r'deep\s*learn|nlp\s*eng|computer\s*vision': 'Data Scientist',

    # Software Engineering
    r'full\s*stack|fullstack': 'Développeur Full Stack',
    r'back[\s-]*end|backend': 'Développeur Backend',
    r'front[\s-]*end|frontend': 'Développeur Frontend',
    r'dev(eloppeur|eloper)?\s+mobile|ios\s+dev|android\s+dev': 'Développeur Mobile',

    # Infrastructure & Cloud
    r'devops|sre|site\s*reliab': 'DevOps / SRE',
    r'cloud\s*(arch|eng|admin)|aws\s+eng|gcp\s+eng|azure\s+eng': 'Cloud Engineer',
    r'sys(admin|tème)|réseau\s+inf|network\s+eng': 'Admin Systèmes & Réseaux',

    # Cybersécurité
    r'cyber|sécurité\s+info|pentester|soc\s+anal': 'Cybersécurité',

    # Management
    r'chef\s+de\s+proj(et)?|project\s+man|scrum\s*master': 'Chef de Projet IT',
    r'architect(e)?\s+(log|tech|data|cloud|sol)': 'Architecte IT',
}


# ════════════════════════════════════════════════════════════════
# Fonctions helper
# ════════════════════════════════════════════════════════════════

def normaliser_ville(ville_brute: str) -> str:
    """Normalise un nom de ville via le mapping."""
    if not ville_brute or not isinstance(ville_brute, str):
        return "Inconnue"
    ville_clean = ville_brute.strip()
    return MAPPING_VILLES.get(ville_clean, MAPPING_VILLES.get(ville_clean.lower(), ville_clean.title()))


def get_region(ville_std: str) -> str:
    """Retourne la région administrative d'une ville normalisée."""
    return MAPPING_REGIONS.get(ville_std, "Autre")


def normaliser_contrat(contrat_brut: str) -> str:
    """Normalise un type de contrat via le mapping."""
    if not contrat_brut or not isinstance(contrat_brut, str):
        return "Non précisé"
    contrat_clean = contrat_brut.strip().lower()
    return MAPPING_CONTRATS.get(contrat_clean, contrat_brut.strip())


def ecrire_metadata(chemin_dir: str, metadata: dict):
    """Écrit un fichier _metadata.json dans le dossier spécifié."""
    chemin = os.path.join(chemin_dir, "_metadata.json")
    metadata["date_generation"] = datetime.now().isoformat()
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


class TransformationTracker:
    """Suivi des transformations appliquées pendant le pipeline."""

    def __init__(self):
        self.transformations = []

    def log(self, etape: str, champ: str, regle: str,
            avant: int, apres: int, details: str = ""):
        self.transformations.append({
            "etape": etape,
            "champ": champ,
            "regle": regle,
            "lignes_avant": avant,
            "lignes_apres": apres,
            "lignes_modifiees": avant - apres if avant != apres else "N/A",
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def generer_rapport(self, chemin_sortie: str):
        """Génère le rapport Markdown des transformations."""
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            f.write("# Rapport de Pipeline — Transformations Appliquées\n\n")
            f.write(f"**Date d'exécution** : {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
            f.write("---\n\n")

            etapes_vues = set()
            for t in self.transformations:
                etape = t["etape"]
                if etape not in etapes_vues:
                    etapes_vues.add(etape)
                    f.write(f"## {etape}\n\n")
                    f.write("| Champ | Règle appliquée | Avant | Après | Détails |\n")
                    f.write("|---|---|---|---|---|\n")

                f.write(f"| `{t['champ']}` | {t['regle']} | {t['lignes_avant']} "
                        f"| {t['lignes_apres']} | {t['details']} |\n")

            f.write("\n---\n\n*Rapport auto-généré par le pipeline Mexora RH.*\n")

        return chemin_sortie
