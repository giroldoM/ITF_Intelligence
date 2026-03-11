import pandas as pd
import numpy as np
from datetime import datetime

print("--- INICIANDO FASE 1.5: MEGA-FUSÃO E LIMPEZA ---")

# 1. Carregar os DOIS ficheiros raw
print("A carregar os ficheiros RAW...")
df_raw1 = pd.read_csv("itf_matches_COMPLETO_RAW.csv")
df_raw2 = pd.read_csv("itf_matches_FANTASMAS_RAW.csv")

# A GRANDE FUSÃO!
df_matches = pd.concat([df_raw1, df_raw2], ignore_index=True)
print(f"Total de jogos brutos fundidos: {len(df_matches)}")

# 2. Carregar apenas os Top 4000 originais (a nossa "nobreza")
df_players = pd.read_csv("jogadores_ids_top4000_enriched.csv")

# Garantir strings
df_matches['Player_ID'] = df_matches['Player_ID'].astype(str).str.replace('.0', '', regex=False)
df_matches['Opponent_ID'] = df_matches['Opponent_ID'].astype(str).str.replace('.0', '', regex=False)
df_players['Player_ID'] = df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)

# Remover jogos sem oponente
df_matches = df_matches[df_matches['Opponent_ID'] != 'nan']

# Parse de datas
def parse_itf_date(date_str):
    try:
        if pd.isna(date_str): return None
        parts = date_str.split(' to ')
        if len(parts) == 2:
            ano = parts[1][-4:] 
            start_date_str = parts[0].strip()
            if len(start_date_str) <= 6: start_date_str = f"{start_date_str} {ano}"
            dt_obj = datetime.strptime(start_date_str, '%d %b %Y')
            return dt_obj.strftime('%Y-%m-%d')
    except:
        return None
    return None

print("A processar datas e inverter Vencedor/Perdedor...")
df_matches['Tourney_Date'] = df_matches['Date'].apply(parse_itf_date)
df_matches = df_matches.dropna(subset=['Tourney_Date']) 

df_matches['winner_id'] = np.where(df_matches['Result'] == 'W', df_matches['Player_ID'], df_matches['Opponent_ID'])
df_matches['loser_id'] = np.where(df_matches['Result'] == 'W', df_matches['Opponent_ID'], df_matches['Player_ID'])

# Desduplicação (Aqui vamos limpar MUITO lixo, porque os Grau 1 cruzam com os Top 4000)
def criar_id_partida(row):
    p1, p2 = sorted([str(row['winner_id']), str(row['loser_id'])])
    return f"{row['Tourney_Date']}_{p1}_{p2}_{row['Round']}"

print("A caçar e remover duplicados na rede...")
df_matches['Match_ID'] = df_matches.apply(criar_id_partida, axis=1)
tamanho_antes = len(df_matches)
df_matches = df_matches.drop_duplicates(subset=['Match_ID'])
print(f" -> Duplicados removidos na mega-base: {tamanho_antes - len(df_matches)} partidas.")

# Padronizar rondas
round_map = {
    'Final': 'F', 'Semi-final': 'SF', 'Quarter-final': 'QF',
    '4th Round': 'R16', '3rd Round': 'R32', '2nd Round': 'R64', '1st Round': 'R128',
    'Round Robin Group 1': 'RR', 'Round Robin Group 2': 'RR',
    'Round Robin Group 3': 'RR', 'Round Robin Group 4': 'RR'
}
df_matches['Round_Clean'] = df_matches['Round'].map(lambda x: round_map.get(x, x)) 

# A CRIAÇÃO DE TODOS OS FANTASMAS (Grau 1 e Grau 2 juntos!)
print("A catalogar todos os Fantasmas da rede...")
todos_oponentes_ids = set(df_matches['Opponent_ID'].unique())
jogadores_top4000 = set(df_players['Player_ID'].unique())

fantasmas_ids = todos_oponentes_ids - jogadores_top4000

df_fantasmas = df_matches[df_matches['Opponent_ID'].isin(fantasmas_ids)][
    ['Opponent_ID', 'Opponent_Name', 'Opponent_Nation']
].drop_duplicates('Opponent_ID')

df_fantasmas = df_fantasmas.rename(columns={
    'Opponent_ID': 'Player_ID', 'Opponent_Name': 'Name', 'Opponent_Nation': 'Nationality'
})

df_fantasmas['Rank'] = np.nan
df_fantasmas['Birth_Year'] = np.nan
df_fantasmas['Play_Hand'] = 'Unknown'
df_fantasmas['Backhand'] = 'Unknown'
df_fantasmas['is_ghost'] = True

df_players['is_ghost'] = False

dim_players = pd.concat([df_players, df_fantasmas], ignore_index=True)
print(f" -> Catalogados {len(df_fantasmas)} jogadores Fantasmas (Grau 1 e 2).")
print(f" -> População Total do Universo ITF: {len(dim_players)} atletas.")

colunas_finais = [
    'Match_ID', 'Tourney_Date', 'Tournament', 'Year', 'Surface', 
    'Round_Clean', 'winner_id', 'loser_id', 'Score'
]
fact_matches_clean = df_matches[colunas_finais].sort_values('Tourney_Date')

fact_matches_clean.to_csv("fact_matches_clean.csv", index=False)
dim_players.to_csv("dim_players.csv", index=False)

print("\n--- MEGA-FUSÃO CONCLUÍDA! PRONTO PARA O ELO! ---")