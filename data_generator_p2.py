import json
import csv
import random
from datetime import datetime, timedelta

def generate_data():
    print("Generation des donnees en cours (5000 offres)...")

    # 1. Fichier : referentiel_competences_it.json
    referentiel = {
      "familles": {
        "langages": {"python": ["python", "python3", "py"], "javascript": ["javascript", "js", "node.js", "nodejs", "node"], "java": ["java", "java8", "java11", "java17"], "sql": ["sql", "mysql", "postgresql", "postgres", "oracle", "tsql"], "r": ["r", "rlang", "r-studio"]},
        "frameworks_web": {"react": ["react", "reactjs", "react.js"], "angular": ["angular", "angularjs"], "django": ["django", "django rest"], "spring": ["spring", "spring boot", "springboot"]},
        "data_engineering": {"spark": ["spark", "apache spark", "pyspark"], "kafka": ["kafka", "apache kafka"], "airflow": ["airflow", "apache airflow"], "dbt": ["dbt", "data build tool"], "hadoop": ["hadoop", "hdfs", "mapreduce"]},
        "cloud": {"aws": ["aws", "amazon web services", "ec2", "s3", "lambda"], "gcp": ["gcp", "google cloud", "bigquery", "cloud storage"], "azure": ["azure", "microsoft azure", "synapse"]},
        "bi_analytics": {"power_bi": ["power bi", "powerbi", "pbi"], "tableau": ["tableau", "tableau desktop"], "metabase": ["metabase"], "looker": ["looker", "looker studio"]}
      }
    }
    with open('referentiel_competences_it.json', 'w', encoding='utf-8') as f:
        json.dump(referentiel, f, ensure_ascii=False, indent=2)

    # 2. Fichier : entreprises_it_maroc.csv
    entreprises = [
        {"nom_entreprise": "TechMaroc SARL", "secteur": "Informatique", "taille": "PME", "ville_siege": "Casablanca", "site_web": "techmaroc.ma", "type": "SSII"},
        {"nom_entreprise": "DataWize", "secteur": "Data", "taille": "Startup", "ville_siege": "Tanger", "site_web": "datawize.com", "type": "Conseil"},
        {"nom_entreprise": "BankAlMaghrib", "secteur": "Banque", "taille": "Grande Entreprise", "ville_siege": "Rabat", "site_web": "bkam.ma", "type": "Banque"},
        {"nom_entreprise": "TangerMedTech", "secteur": "Logistique", "taille": "ETI", "ville_siege": "Tanger", "site_web": "tmtech.ma", "type": "Produit"},
        {"nom_entreprise": "Inwi", "secteur": "Telecom", "taille": "Grande Entreprise", "ville_siege": "Casablanca", "site_web": "inwi.ma", "type": "Telecom"}
    ]
    with open('entreprises_it_maroc.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=entreprises[0].keys())
        writer.writeheader()
        writer.writerows(entreprises)

    # 3. Fichier : offres_emploi_it_maroc.json (5000 lignes)
    titres = ["Dev Data", "Ingénieur Big Data", "Data Eng.", "Développeur BI", "Data Engineer Junior", "Développeur Full Stack React/Node.js", "Data Scientist", "DevOps", "SysAdmin"]
    villes = ["casa", "CASABLANCA", "Casablanca", "Tanger", "Rabat", "Marrakech", "Fès"]
    contrats = ["CDI", "cdi", "Contrat à durée indéterminée", "Permanent", "Freelance"]
    exps = ["3-5 ans", "3 à 5 ans", "min 3 ans", "Débutant accepté", None, "Senior (7+ ans)"]
    salaires = ["15000-20000 MAD", "15K-20K", "Selon profil", None, "Confidentiel", "2000 EUR", "8000-12000 dh"]
    competences_list = ["React, Node.js, PostgreSQL", "Python / SQL / Spark", "AWS • Python • Docker", "Java, Spring, Angular", "Power BI, SQL, Excel", "GCP, BigQuery, Airflow"]

    offres = []
    for i in range(5000):
        date_pub = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 600))
        
        offre = {
            "id_offre": f"RK-2024-{i:05d}",
            "source": random.choice(["rekrute", "marocannonce", "linkedin"]),
            "titre_poste": random.choice(titres),
            "description": f"Nous recherchons un profil qualifie. Connaissances exigees : {random.choice(competences_list)}. Travail en equipe Agile.",
            "competences_brut": random.choice(competences_list),
            "entreprise": random.choice(entreprises)["nom_entreprise"],
            "ville": random.choice(villes),
            "type_contrat": random.choice(contrats),
            "experience_requise": random.choice(exps),
            "salaire_brut": random.choice(salaires),
            "niveau_etudes": random.choice(["Bac+5", "Bac+3", "Ingénieur"]),
            "secteur": random.choice(["Informatique / Télécom", "Banque", "Conseil"]),
            "date_publication": date_pub.strftime("%Y-%m-%d"),
            "date_expiration": (date_pub + timedelta(days=30)).strftime("%Y-%m-%d"),
            "nb_postes": random.randint(1, 3),
            "teletravail": random.choice(["Hybride", "Remote", "Présentiel", "télétravail"]),
            "langue_requise": ["Français", "Anglais"]
        }
        
        # Injecter des erreurs intentionnelles de format de date (comme demande)
        if random.random() < 0.05:
            offre["date_publication"] = "15/11/2024" 
            
        offres.append(offre)

    # Injecter des doublons (Erreur intentionnelle)
    offres.extend(offres[:150])

    with open('offres_emploi_it_maroc.json', 'w', encoding='utf-8') as f:
        json.dump({"offres": offres}, f, ensure_ascii=False, indent=2)

    print("Generation terminee ! Les 3 fichiers ont ete crees avec succes.")

if __name__ == "__main__":
    generate_data()
