from curl_cffi import requests
import pandas as pd
import time
import random

print("--- INICIANDO RASPAGEM: TODAS AS JOGADORAS RANQUEADAS ---")

headers_base = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.itftennis.com",
    "Connection": "keep-alive"
}

def criar_nova_sessao():
    s = requests.Session(impersonate="chrome120")
    s.headers.update(headers_base)
    try:
        s.get("https://www.itftennis.com/en/", timeout=10)
    except:
        pass
    return s

sessao = criar_nova_sessao()
jogadoras = []

take = 100
skip = 0

while True:
    url = f"https://www.itftennis.com/tennis/api/PlayerRankApi/GetPlayerRankings?circuitCode=JT&playerTypeCode=G&ageCategoryCode=&juniorRankingType=itf&take={take}&skip={skip}&isOrderAscending=true"
    
    max_tentativas = 3
    sucesso_nesta_pagina = False
    items = []
    
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = sessao.get(url, timeout=15)
            
            if "Incapsula" in response.text or response.status_code != 200:
                print("  -> O segurança (Incapsula) notou. A trocar de disfarce...")
                sessao.cookies.clear()
                try: sessao.get("https://www.itftennis.com/en/", timeout=10)
                except: pass
                time.sleep(random.uniform(3.0, 5.0))
                continue
            
            dados = response.json()
            items = dados.get('items', [])
            sucesso_nesta_pagina = True
            break
            
        except Exception as e:
            print(f"Erro de rede (Tentativa {tentativa}). Aguardando...")
            time.sleep(3)
            
    if not sucesso_nesta_pagina:
        print("Falha definitiva numa página. A avançar para a próxima para não travar...")
        skip += take
        continue

    if len(items) == 0:
        print("\nFim do ranking alcançado!")
        break
        
    for item in items:
        # AQUI ESTÁ A MAGIA CORRIGIDA: Lemos diretamente do "item" com as chaves novas
        rank = item.get('rank')
        player_id = item.get('playerId')
        given_name = item.get('playerGivenName', '')
        family_name = item.get('playerFamilyName', '')
        nationality = item.get('playerNationalityCode', '')
        ano_nascimento = item.get('birthYear', None)
        
        jogadoras.append({
            'Player_ID': player_id,
            'Name': f"{given_name} {family_name}".strip(),
            'Rank': rank,
            'Nationality': nationality,
            'Birth_Year': ano_nascimento,
            'Play_Hand': 'Unknown',
            'Backhand': 'Unknown'
        })
    
    print(f"Extraídas {len(items)} jogadoras (Rank {skip} até {skip+take}). Total até agora: {len(jogadoras)}")
    skip += take
    time.sleep(random.uniform(1.0, 2.0))

# Tratamento Final e Salvamento
df_jogadoras = pd.DataFrame(jogadoras)
df_jogadoras = df_jogadoras.drop_duplicates(subset=['Player_ID'])

arquivo_saida = "jogadoras_ids_top4000_enriched.csv"
df_jogadoras.to_csv(arquivo_saida, index=False)

print(f"\n--- SUCESSO! ---")
print(f"{len(df_jogadoras)} atletas femininas guardadas em '{arquivo_saida}'.")