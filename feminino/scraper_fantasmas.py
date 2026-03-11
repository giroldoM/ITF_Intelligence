from curl_cffi import requests
import pandas as pd
import time
import os
import random

print("--- ONDA 2 FEMININA: RASPAGEM DAS FANTASMAS ---")

arquivo_raw = "itf_matches_COMPLETO_RAW_W.csv"
arquivo_jogadoras = "jogadoras_ids_top4000_enriched.csv"
arquivo_saida = "itf_matches_FANTASMAS_RAW_W.csv"

# 1. Descobrir quem são as Fantasmas
df_raw = pd.read_csv(arquivo_raw)
df_players = pd.read_csv(arquivo_jogadoras)

df_raw['Opponent_ID'] = df_raw['Opponent_ID'].astype(str).str.replace('.0', '', regex=False)
df_players['Player_ID'] = df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)

todos_oponentes = set(df_raw[df_raw['Opponent_ID'] != 'nan']['Opponent_ID'].unique())
jogadoras_conhecidas = set(df_players['Player_ID'].unique())
fantasmas_ids = list(todos_oponentes - jogadoras_conhecidas)

total_fantasmas = len(fantasmas_ids)
print(f"Total de Fantasmas Grau 1 a raspar: {total_fantasmas}")

# 2. Sistema de Retomada
todas_as_partidas = []
ids_ja_processados = set()

if os.path.exists(arquivo_saida):
    df_existente = pd.read_csv(arquivo_saida)
    todas_as_partidas = df_existente.to_dict('records')
    ids_ja_processados = set(df_existente['Player_ID'].astype(str).str.replace('.0', '', regex=False).unique())
    print(f"Já extraídas: {len(ids_ja_processados)}. Faltam: {total_fantasmas - len(ids_ja_processados)}")

headers_base = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Origin": "https://www.itftennis.com",
    "Connection": "keep-alive"
}

def criar_nova_sessao():
    s = requests.Session(impersonate="chrome120")
    s.headers.update(headers_base)
    try: s.get("https://www.itftennis.com/en/", timeout=10)
    except: pass
    return s

sessao = criar_nova_sessao()

# 3. Loop de Extração
for i, player_id in enumerate(fantasmas_ids, start=1):
    if player_id in ids_ja_processados: continue
        
    url_api = f"https://www.itftennis.com/tennis/api/PlayerApi/GetPlayerActivity?circuitCode=JT&matchTypeCode=S&playerId={player_id}&skip=0&take=1000"
    
    for tentativa in range(1, 4):
        try:
            response = sessao.get(url_api, timeout=12)
            if "Incapsula" in response.text or response.status_code != 200:
                sessao = criar_nova_sessao()
                time.sleep(random.uniform(3.0, 5.0))
                continue
                
            try: dados_json = response.json()
            except:
                sessao = criar_nova_sessao()
                time.sleep(random.uniform(3.0, 5.0))
                continue

            jogos = 0
            for torneio in dados_json.get('items', []):
                for evento in torneio.get('events', []):
                    for p in evento.get('matches', []):
                        if p.get('resultStatusCode') in ['BYE', 'WO'] or p.get('resultCode') == 'B': continue
                        
                        op = p.get('opponents', [{}])[0] if p.get('opponents') else {}
                        
                        placar = " ".join([f"{s.get('scoreOne')}-{s.get('scoreTwo')}" for s in p.get('scores', [])])
                        
                        todas_as_partidas.append({
                            'Player_ID': player_id,
                            'Opponent_ID': op.get('playerId'),
                            'Opponent_Name': f"{op.get('givenName')} {op.get('familyName')}".strip() if op else "Desconhecido",
                            'Opponent_Nation': op.get('nationality'),
                            'Tournament': torneio.get('tournamentName'),
                            'Year': torneio.get('dates', '')[-4:],
                            'Date': torneio.get('dates'),
                            'Surface': torneio.get('surfaceDesc'),
                            'Round': p.get('roundGroup', {}).get('Value'),
                            'Result': p.get('resultCode'),
                            'Score': placar.strip()
                        })
                        jogos += 1
            
            print(f"[{i}/{total_fantasmas}] Fantasma {player_id}: {jogos} jogos.")
            ids_ja_processados.add(player_id)
            break
        except: time.sleep(3)

    if len(ids_ja_processados) % 50 == 0:
        pd.DataFrame(todas_as_partidas).to_csv(arquivo_saida, index=False)
    time.sleep(random.uniform(1.0, 2.0))

pd.DataFrame(todas_as_partidas).to_csv(arquivo_saida, index=False)
print("--- RASPAGEM DE FANTASMAS CONCLUÍDA ---")