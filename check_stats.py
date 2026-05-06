import duckdb, os
con = duckdb.connect()
lake = 'data_lake_mexora_rh'
gold = lake + '/gold'
silver = lake + '/silver'

for f in os.listdir(gold):
    if f.endswith('.parquet'):
        n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{gold}/{f}')").fetchone()[0]
        print(f'{f}: {n} rows')

print('\n--- TOP 10 COMPETENCES ---')
for r in con.execute(f"SELECT competence, SUM(nb_offres_mentionnent) as n FROM read_parquet('{gold}/top_competences.parquet') WHERE competence!='non_detecte' GROUP BY competence ORDER BY n DESC LIMIT 10").fetchall():
    print(f'  {r[0]}: {r[1]}')

print('\n--- SALAIRES PAR PROFIL ---')
for r in con.execute(f"SELECT profil, SUM(nb_offres) as n, ROUND(MEDIAN(salaire_median_mad),0) as med FROM read_parquet('{gold}/salaires_par_profil.parquet') GROUP BY profil ORDER BY med DESC NULLS LAST").fetchall():
    print(f'  {r[0]}: {r[1]} offres, median={r[2]}')

print('\n--- OFFRES PAR VILLE ---')
for r in con.execute(f"SELECT ville, SUM(nb_offres) as n FROM read_parquet('{gold}/offres_par_ville.parquet') GROUP BY ville ORDER BY n DESC").fetchall():
    print(f'  {r[0]}: {r[1]}')

print('\n--- TOP 5 ENTREPRISES ---')
for r in con.execute(f"SELECT entreprise, ville, nb_offres_publiees FROM read_parquet('{gold}/entreprises_recruteurs.parquet') ORDER BY nb_offres_publiees DESC LIMIT 5").fetchall():
    print(f'  {r[0]} ({r[1]}): {r[2]}')

print('\n--- SILVER STATS ---')
r = con.execute(f"SELECT COUNT(*) as total, COUNT(DISTINCT profil_normalise) as profils, COUNT(DISTINCT ville_std) as villes FROM read_parquet('{silver}/offres_clean/offres_clean.parquet')").fetchone()
print(f'  Total: {r[0]}, Profils: {r[1]}, Villes: {r[2]}')

for r in con.execute(f"SELECT profil_normalise, COUNT(*) as n FROM read_parquet('{silver}/offres_clean/offres_clean.parquet') GROUP BY profil_normalise ORDER BY n DESC").fetchall():
    print(f'  {r[0]}: {r[1]}')

print('\n--- REMOTE PAR VILLE ---')
for r in con.execute(f"SELECT ville, SUM(nb_offres) as total, SUM(nb_offres_remote) as remote, ROUND(SUM(nb_offres_remote)*100.0/SUM(nb_offres),1) as pct FROM read_parquet('{gold}/offres_par_ville.parquet') GROUP BY ville ORDER BY total DESC").fetchall():
    print(f'  {r[0]}: total={r[1]}, remote={r[2]}, pct={r[3]}%')

print('\n--- SALAIRE DETAILS ---')
for r in con.execute(f"SELECT profil, SUM(nb_offres) as n, MIN(salaire_min_observe) as smin, ROUND(MEDIAN(salaire_median_mad),0) as med, MAX(salaire_max_observe) as smax FROM read_parquet('{gold}/salaires_par_profil.parquet') GROUP BY profil ORDER BY med DESC NULLS LAST").fetchall():
    print(f'  {r[0]}: n={r[1]}, min={r[2]}, med={r[3]}, max={r[4]}')

print('\n--- COMPETENCES PAR PROFIL DATA ---')
for r in con.execute(f"SELECT profil, competence, nb_offres_mentionnent, rang_dans_profil FROM read_parquet('{gold}/top_competences.parquet') WHERE profil IN ('Data Engineer','Data Analyst','Data Scientist','Autre IT') AND rang_dans_profil<=5 ORDER BY profil, rang_dans_profil").fetchall():
    print(f'  {r[0]} #{r[3]}: {r[1]} ({r[2]})')
