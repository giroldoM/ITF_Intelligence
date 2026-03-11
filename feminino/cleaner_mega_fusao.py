import pandas as pd
import numpy as np
from datetime import datetime

print("--- MEGA-FUSÃO FEMININA E LIMPEZA ---")

df_raw1 = pd.read_csv("itf_matches_COMPLETO_RAW_W.csv")
df_raw2 = pd.read_csv("itf_matches_FANTASMAS_RAW_W.csv")
df_matches = pd.concat([df_raw1, df_raw2], ignore_index=True)

df_players = pd.read_csv("jogadoras_ids_top4000_enriched.csv")

df_matches['Player_ID'] = df_matches['Player_ID'].astype(str).str.replace('.0', '', regex=False)
df_matches['Opponent_ID'] = df_matches['Opponent_ID'].astype(str).str.replace('.0', '', regex=False)
df_players['Player_ID'] = df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)

df_matches = df_matches[df_matches['Opponent_ID'] != 'nan']

def parse_itf_date(date_str):
    try:
        if pd.isna(date_str): return None
        parts = date_str.split(' to ')
        if len(parts) == 2:
            ano = parts[1][-4:] 
            start_date_str = parts[0].strip()
            if len(start_date_str) <= 6: start_date_str = f"{start_date_str} {ano}"
            return datetime.strptime(start_date_str, '%d %b %Y').strftime('%Y-%m-%d')
    except: return None
    return None

df_matches['Tourney_Date'] = df_matches['Date'].apply(parse_itf_date)
df_matches = df_matches.dropna(subset=['Tourney_Date']) 

df_matches['winner_id'] = np.where(df_matches['Result'] == 'W', df_matches['Player_ID'], df_matches['Opponent_ID'])
df_matches['loser_id'] = np.where(df_matches['Result'] == 'W', df_matches['Opponent_ID'], df_matches['Player_ID'])

def criar_id_partida(row):
    p1, p2 = sorted([str(row['winner_id']), str(row['loser_id'])])
    return f"{row['Tourney_Date']}_{p1}_{p2}_{row['Round']}"

df_matches['Match_ID'] = df_matches.apply(criar_id_partida, axis=1)
df_matches = df_matches.drop_duplicates(subset=['Match_ID'])

round_map = {
    'Final': 'F', 'Semi-final': 'SF', 'Quarter-final': 'QF',
    '4th Round': 'R16', '3rd Round': 'R32', '2nd Round': 'R64', '1st Round': 'R128',
    'Round Robin Group 1': 'RR', 'Round Robin Group 2': 'RR', 'Round Robin Group 3': 'RR'
}
df_matches['Round_Clean'] = df_matches['Round'].map(lambda x: round_map.get(x, x)) 

todos_oponentes_ids = set(df_matches['Opponent_ID'].unique())
jogadoras_top4000 = set(df_players['Player_ID'].unique())
fantasmas_ids = todos_oponentes_ids - jogadoras_top4000

df_fantasmas = df_matches[df_matches['Opponent_ID'].isin(fantasmas_ids)][['Opponent_ID', 'Opponent_Name', 'Opponent_Nation']].drop_duplicates('Opponent_ID')
df_fantasmas = df_fantasmas.rename(columns={'Opponent_ID': 'Player_ID', 'Opponent_Name': 'Name', 'Opponent_Nation': 'Nationality'})
df_fantasmas['Rank'] = np.nan
df_fantasmas['Birth_Year'] = np.nan
df_fantasmas['is_ghost'] = True
df_players['is_ghost'] = False

dim_players = pd.concat([df_players, df_fantasmas], ignore_index=True)

colunas_finais = ['Match_ID', 'Tourney_Date', 'Tournament', 'Year', 'Surface', 'Round_Clean', 'winner_id', 'loser_id', 'Score']
fact_matches_clean = df_matches[colunas_finais].sort_values('Tourney_Date')

fact_matches_clean.to_csv("fact_matches_clean_W.csv", index=False)
dim_players.to_csv("dim_players_W.csv", index=False)
print("--- MEGA-FUSÃO CONCLUÍDA! PRONTO PARA O ELO! ---")