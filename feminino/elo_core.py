import pandas as pd

print("--- MOTOR DE ELO FEMININO ---")

df_players = pd.read_csv("dim_players_W.csv")
df_matches = pd.read_csv("fact_matches_clean_W.csv")

df_players['Player_ID'] = df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)
df_matches['winner_id'] = df_matches['winner_id'].astype(str).str.replace('.0', '', regex=False)
df_matches['loser_id'] = df_matches['loser_id'].astype(str).str.replace('.0', '', regex=False)
df_matches = df_matches.sort_values(by='Tourney_Date').reset_index(drop=True)

elo_global, elo_surface = {}, {}
matches_played, matches_surface = {}, {}
ELO_INICIAL = 1500.0

def calc_prob(elo_a, elo_b): return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
def get_k(jogos): return 60 if jogos < 10 else 40 if jogos < 25 else 30 if jogos < 50 else 20
def calc_shrinkage(global_e, raw_surf_e, jogos_surf):
    alpha = max(0, 1 - (jogos_surf / 20.0))
    return (alpha * global_e) + ((1 - alpha) * raw_surf_e)

w_elo_pre, l_elo_pre, w_surf_elo_pre, l_surf_elo_pre = [], [], [], []

for i, row in df_matches.iterrows():
    w_id, l_id, surf = row['winner_id'], row['loser_id'], row['Surface']
    
    w_elo = elo_global.get(w_id, ELO_INICIAL)
    l_elo = elo_global.get(l_id, ELO_INICIAL)
    w_surf = elo_surface.get((w_id, surf), ELO_INICIAL)
    l_surf = elo_surface.get((l_id, surf), ELO_INICIAL)
    w_c, l_c = matches_played.get(w_id, 0), matches_played.get(l_id, 0)
    w_sc, l_sc = matches_surface.get((w_id, surf), 0), matches_surface.get((l_id, surf), 0)
    
    w_surf_blend = calc_shrinkage(w_elo, w_surf, w_sc)
    l_surf_blend = calc_shrinkage(l_elo, l_surf, l_sc)
    
    w_elo_pre.append(w_elo); l_elo_pre.append(l_elo)
    w_surf_elo_pre.append(w_surf_blend); l_surf_elo_pre.append(l_surf_blend)
    
    exp_w = calc_prob(w_elo, l_elo)
    exp_l = calc_prob(l_elo, w_elo) 
    exp_w_s = calc_prob(w_surf, l_surf)
    exp_l_s = calc_prob(l_surf, w_surf)
    
    kw, kl = get_k(w_c), get_k(l_c)
    
    elo_global[w_id] = w_elo + kw * (1 - exp_w)
    elo_global[l_id] = l_elo + kl * (0 - exp_l)
    
    if pd.notna(surf) and surf != 'Unknown':
        elo_surface[(w_id, surf)] = w_surf + kw * (1 - exp_w_s)
        elo_surface[(l_id, surf)] = l_surf + kl * (0 - exp_l_s)
        matches_surface[(w_id, surf)] = w_sc + 1; matches_surface[(l_id, surf)] = l_sc + 1
        
    matches_played[w_id] = w_c + 1; matches_played[l_id] = l_c + 1

df_matches['Winner_Global_Elo'] = w_elo_pre
df_matches['Loser_Global_Elo'] = l_elo_pre
df_matches['Winner_Surface_Elo'] = w_surf_elo_pre
df_matches['Loser_Surface_Elo'] = l_surf_elo_pre

df_matches.to_csv("fact_matches_with_elo_W.csv", index=False)

print("\n--- TOP 15 JOGADORAS ATUAIS ---")
df_rank = pd.DataFrame(list(elo_global.items()), columns=['Player_ID', 'Current_Elo']).merge(df_players[['Player_ID', 'Name']], on='Player_ID', how='left')
print(df_rank.sort_values(by='Current_Elo', ascending=False).head(15)[['Name', 'Current_Elo']].to_string(index=False))