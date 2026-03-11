import pandas as pd
import numpy as np

print("--- INICIANDO FASE 3: CRIAÇÃO DO DATASET DE MACHINE LEARNING ---")

# 1. Carregar Dados
print("A carregar os jogos com Elo e o registo de jogadores...")
df_matches = pd.read_csv("fact_matches_with_elo.csv")
df_players = pd.read_csv("dim_players.csv")

# Converter o ano de nascimento para numérico
df_players['Birth_Year'] = pd.to_numeric(df_players['Birth_Year'], errors='coerce')

# 2. O Corte Temporal (Remover o Burn-in)
tamanho_antes = len(df_matches)
df_matches['Year'] = pd.to_numeric(df_matches['Year'], errors='coerce')
df_matches = df_matches[df_matches['Year'] >= 2023].copy()
print(f"Jogos do período de Burn-in (2021-2022) descartados: {tamanho_antes - len(df_matches)}")

# 3. Juntar as informações de Nascimento para calcular a Idade
df_matches = df_matches.merge(df_players[['Player_ID', 'Birth_Year']], 
                              left_on='winner_id', right_on='Player_ID', how='left')
df_matches = df_matches.rename(columns={'Birth_Year': 'w_birth_year'})

df_matches = df_matches.merge(df_players[['Player_ID', 'Birth_Year']], 
                              left_on='loser_id', right_on='Player_ID', how='left')
df_matches = df_matches.rename(columns={'Birth_Year': 'l_birth_year'})

# Imputar 16 anos para os fantasmas (Ano do torneio - 16)
df_matches['w_birth_year'] = df_matches['w_birth_year'].fillna(df_matches['Year'] - 16)
df_matches['l_birth_year'] = df_matches['l_birth_year'].fillna(df_matches['Year'] - 16)

# Calcular a Idade no momento do jogo
df_matches['w_age'] = df_matches['Year'] - df_matches['w_birth_year']
df_matches['l_age'] = df_matches['Year'] - df_matches['l_birth_year']

# 4. RANDOMIZAÇÃO (P1 vs P2)
print("A randomizar os dados para criar o Target (y)...")
np.random.seed(42) # Para ser reprodutível
# Criar um array de booleanos (True/False) com 50% de probabilidade
is_winner_p1 = np.random.rand(len(df_matches)) > 0.5

# Construir as colunas do Jogador 1 e Jogador 2
df_ml = pd.DataFrame()
df_ml['Tourney_Date'] = df_matches['Tourney_Date']
df_ml['Year'] = df_matches['Year']
df_ml['Surface'] = df_matches['Surface']
df_ml['Round'] = df_matches['Round_Clean']

# Atribuição baseada no sorteio
df_ml['p1_id'] = np.where(is_winner_p1, df_matches['winner_id'], df_matches['loser_id'])
df_ml['p2_id'] = np.where(is_winner_p1, df_matches['loser_id'], df_matches['winner_id'])

# Features Base
p1_elo = np.where(is_winner_p1, df_matches['Winner_Global_Elo'], df_matches['Loser_Global_Elo'])
p2_elo = np.where(is_winner_p1, df_matches['Loser_Global_Elo'], df_matches['Winner_Global_Elo'])

p1_surf_elo = np.where(is_winner_p1, df_matches['Winner_Surface_Elo'], df_matches['Loser_Surface_Elo'])
p2_surf_elo = np.where(is_winner_p1, df_matches['Loser_Surface_Elo'], df_matches['Winner_Surface_Elo'])

p1_age = np.where(is_winner_p1, df_matches['w_age'], df_matches['l_age'])
p2_age = np.where(is_winner_p1, df_matches['l_age'], df_matches['w_age'])

# 5. AS FEATURES DIFERENCIAIS (O OURO DO XGBOOST)
print("A calcular as diferenças de forças (Features)...")
df_ml['elo_diff'] = p1_elo - p2_elo
df_ml['surface_elo_diff'] = p1_surf_elo - p2_surf_elo
df_ml['age_diff'] = p1_age - p2_age

# A nossa variável ALVO (Se o P1 ganhou = 1, Se o P2 ganhou = 0)
df_ml['target'] = is_winner_p1.astype(int)

# Limpeza final de nulos criados por lixo residual
df_ml = df_ml.dropna(subset=['elo_diff', 'surface_elo_diff', 'age_diff'])

df_ml.to_csv("dataset_ml_final.csv", index=False)
print("\n--- FASE 3 CONCLUÍDA! ---")
print(f"Dataset de Treino/Teste gerado com {len(df_ml)} jogos equilibrados (50% vitórias P1, 50% vitórias P2).")
print("O ficheiro 'dataset_ml_final.csv' está pronto para ser injetado no XGBoost!")