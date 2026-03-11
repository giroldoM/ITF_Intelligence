import pandas as pd
import numpy as np

print("--- CONSTRUÇÃO DE FEATURES (FEMININO) ---")

df_matches = pd.read_csv("fact_matches_with_elo_W.csv")
df_players = pd.read_csv("dim_players_W.csv")

df_players['Birth_Year'] = pd.to_numeric(df_players['Birth_Year'], errors='coerce')
df_matches['Year'] = pd.to_numeric(df_matches['Year'], errors='coerce')
df_matches = df_matches[df_matches['Year'] >= 2023].copy()

df_matches = df_matches.merge(df_players[['Player_ID', 'Birth_Year']], left_on='winner_id', right_on='Player_ID', how='left').rename(columns={'Birth_Year': 'w_birth_year'})
df_matches = df_matches.merge(df_players[['Player_ID', 'Birth_Year']], left_on='loser_id', right_on='Player_ID', how='left').rename(columns={'Birth_Year': 'l_birth_year'})

df_matches['w_birth_year'] = df_matches['w_birth_year'].fillna(df_matches['Year'] - 16)
df_matches['l_birth_year'] = df_matches['l_birth_year'].fillna(df_matches['Year'] - 16)
df_matches['w_age'] = df_matches['Year'] - df_matches['w_birth_year']
df_matches['l_age'] = df_matches['Year'] - df_matches['l_birth_year']

np.random.seed(42)
is_winner_p1 = np.random.rand(len(df_matches)) > 0.5

df_ml = pd.DataFrame()
df_ml['Tourney_Date'] = df_matches['Tourney_Date']
df_ml['Year'] = df_matches['Year']
df_ml['Surface'] = df_matches['Surface']
df_ml['Round'] = df_matches['Round_Clean']

df_ml['p1_id'] = np.where(is_winner_p1, df_matches['winner_id'], df_matches['loser_id'])
df_ml['p2_id'] = np.where(is_winner_p1, df_matches['loser_id'], df_matches['winner_id'])

p1_elo = np.where(is_winner_p1, df_matches['Winner_Global_Elo'], df_matches['Loser_Global_Elo'])
p2_elo = np.where(is_winner_p1, df_matches['Loser_Global_Elo'], df_matches['Winner_Global_Elo'])
p1_surf_elo = np.where(is_winner_p1, df_matches['Winner_Surface_Elo'], df_matches['Loser_Surface_Elo'])
p2_surf_elo = np.where(is_winner_p1, df_matches['Loser_Surface_Elo'], df_matches['Winner_Surface_Elo'])
p1_age = np.where(is_winner_p1, df_matches['w_age'], df_matches['l_age'])
p2_age = np.where(is_winner_p1, df_matches['l_age'], df_matches['w_age'])

df_ml['elo_diff'] = p1_elo - p2_elo
df_ml['surface_elo_diff'] = p1_surf_elo - p2_surf_elo
df_ml['age_diff'] = p1_age - p2_age
df_ml['target'] = is_winner_p1.astype(int)

df_ml = df_ml.dropna(subset=['elo_diff', 'surface_elo_diff', 'age_diff'])
df_ml.to_csv("dataset_ml_final_W.csv", index=False)
print("--- DATASET ML FEMININO GERADO COM SUCESSO ---")