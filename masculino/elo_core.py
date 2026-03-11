import pandas as pd
import numpy as np

print("--- INICIANDO FASE 2: MOTOR DE ELO DINÂMICO ---")

ficheiro_jogadores = "dim_players.csv"
ficheiro_jogos = "fact_matches_clean.csv"

# 1. Carregar Dados e Forçar IDs como String (Blindagem contra o Pandas)
print("A carregar base limpa e a ordenar cronologicamente...")
df_players = pd.read_csv(ficheiro_jogadores)
df_matches = pd.read_csv(ficheiro_jogos)

df_players['Player_ID'] = df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)
df_matches['winner_id'] = df_matches['winner_id'].astype(str).str.replace('.0', '', regex=False)
df_matches['loser_id'] = df_matches['loser_id'].astype(str).str.replace('.0', '', regex=False)

# Garantir ordenação temporal rigorosa para evitar Leakage (Ver o futuro)
df_matches = df_matches.sort_values(by='Tourney_Date').reset_index(drop=True)

# 2. Dicionários de Estado (A "Memória" da Engine)
elo_global = {}         # dict: player_id -> elo
elo_surface = {}        # dict: (player_id, surface) -> elo
matches_played = {}     # dict: player_id -> int
matches_surface = {}    # dict: (player_id, surface) -> int

ELO_INICIAL = 1500.0

# 3. Funções Matemáticas do Elo
def calcular_probabilidade(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def get_k_factor(jogos_disputados):
    """K-Factor dinâmico: Alta volatilidade no início, estabilidade no futuro"""
    if jogos_disputados < 10:
        return 60
    elif jogos_disputados < 25:
        return 40
    elif jogos_disputados < 50:
        return 30
    else:
        return 20

def calcular_shrinkage_surface(global_elo, raw_surface_elo, num_jogos_surface):
    """Mistura o Elo Global com o Elo da Superfície"""
    alpha = max(0, 1 - (num_jogos_surface / 20.0))
    return (alpha * global_elo) + ((1 - alpha) * raw_surface_elo)

# 4. Listas para guardar as Features Históricas
w_elo_pre, l_elo_pre = [], []
w_surf_elo_pre, l_surf_elo_pre = [], []

print(f"A simular a passagem do tempo para {len(df_matches)} partidas...")

# 5. O Grande Loop Cronológico
for i, row in df_matches.iterrows():
    w_id = row['winner_id']
    l_id = row['loser_id']
    surf = row['Surface']
    
    # Obter os estados ATUAIS (Pré-Jogo)
    w_elo_atual = elo_global.get(w_id, ELO_INICIAL)
    l_elo_atual = elo_global.get(l_id, ELO_INICIAL)
    
    w_surf_raw = elo_surface.get((w_id, surf), ELO_INICIAL)
    l_surf_raw = elo_surface.get((l_id, surf), ELO_INICIAL)
    
    w_count = matches_played.get(w_id, 0)
    l_count = matches_played.get(l_id, 0)
    
    w_surf_count = matches_surface.get((w_id, surf), 0)
    l_surf_count = matches_surface.get((l_id, surf), 0)
    
    # Aplicar o Shrinkage para criar a feature perfeita para o ML
    w_surf_blended = calcular_shrinkage_surface(w_elo_atual, w_surf_raw, w_surf_count)
    l_surf_blended = calcular_shrinkage_surface(l_elo_atual, l_surf_raw, l_surf_count)
    
    # Guardar os valores Pré-Jogo (sem leakage!) nas listas
    w_elo_pre.append(w_elo_atual)
    l_elo_pre.append(l_elo_atual)
    w_surf_elo_pre.append(w_surf_blended)
    l_surf_elo_pre.append(l_surf_blended)
    
    # -- ATUALIZAÇÃO PÓS-JOGO (Aprender com o resultado) --
    exp_w = calcular_probabilidade(w_elo_atual, l_elo_atual)
    exp_l = calcular_probabilidade(l_elo_atual, w_elo_atual) 
    
    exp_w_surf = calcular_probabilidade(w_surf_raw, l_surf_raw)
    exp_l_surf = calcular_probabilidade(l_surf_raw, w_surf_raw)
    
    k_w = get_k_factor(w_count)
    k_l = get_k_factor(l_count)
    
    elo_global[w_id] = w_elo_atual + k_w * (1 - exp_w)
    elo_global[l_id] = l_elo_atual + k_l * (0 - exp_l)
    
    if pd.notna(surf) and surf != 'Unknown':
        elo_surface[(w_id, surf)] = w_surf_raw + k_w * (1 - exp_w_surf)
        elo_surface[(l_id, surf)] = l_surf_raw + k_l * (0 - exp_l_surf)
        matches_surface[(w_id, surf)] = w_surf_count + 1
        matches_surface[(l_id, surf)] = l_surf_count + 1
        
    matches_played[w_id] = w_count + 1
    matches_played[l_id] = l_count + 1

# 6. Adicionar as features ao DataFrame
df_matches['Winner_Global_Elo'] = w_elo_pre
df_matches['Loser_Global_Elo'] = l_elo_pre
df_matches['Winner_Surface_Elo'] = w_surf_elo_pre
df_matches['Loser_Surface_Elo'] = l_surf_elo_pre

ficheiro_saida = "fact_matches_with_elo.csv"
df_matches.to_csv(ficheiro_saida, index=False)

print(f"\nEngine executada! Ficheiro guardado como: {ficheiro_saida}")

# ==========================================
# SANITY CHECK: O TESTE DA REALIDADE
# ==========================================
print("\n--- TOP 15 JOGADORES ATUAIS SEGUNDO O NOSSO ELO ---")

df_ranking_elo = pd.DataFrame(list(elo_global.items()), columns=['Player_ID', 'Current_Elo'])
df_ranking_elo = df_ranking_elo.merge(df_players[['Player_ID', 'Name']], on='Player_ID', how='left')

top_15 = df_ranking_elo.sort_values(by='Current_Elo', ascending=False).head(15)
top_15['Current_Elo'] = top_15['Current_Elo'].round(1)

print(top_15[['Name', 'Current_Elo']].to_string(index=False))