from curl_cffi import requests
import pandas as pd
import time
import os
import random

arquivo_ids = "jogadores_ids_top4000.csv"
arquivo_enriquecido = "jogadores_ids_top4000_enriched.csv"

if os.path.exists(arquivo_enriquecido):
    print("Arquivo de progresso encontrado! Retomando e corrigindo erros...")
    df = pd.read_csv(arquivo_enriquecido)
else:
    print(f"Lendo o arquivo base {arquivo_ids}...")
    df = pd.read_csv(arquivo_ids)
    df['Play_Hand'] = None
    df['Backhand'] = None

headers_base = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.itftennis.com",
    "Connection": "keep-alive"
}

print("Preparando o disfarce inicial ÚNICO...")
# Criamos a sessão uma única vez fora do loop para não travar o DNS do Mac
sessao = requests.Session(impersonate="chrome120")
sessao.headers.update(headers_base)

try:
    sessao.get("https://www.itftennis.com/en/", timeout=15)
except:
    pass

total_jogadores = len(df)
print(f"\nIniciando a extração...\n")

for index, row in df.iterrows():
    
    if pd.notna(row['Play_Hand']) and row['Play_Hand'] != 'Error':
        continue

    player_id = str(row['Player_ID'])
    url_api = f"https://www.itftennis.com/tennis/api/PlayerApi/GetHeadToHeadPlayerDetails?circuitCode=JT&playerId={player_id}"
    
    max_tentativas = 3
    sucesso_req = False
    ultimo_erro = ""

    for tentativa in range(1, max_tentativas + 1):
        try:
            sessao.headers.update({"Referer": f"https://www.itftennis.com/en/head-to-head/?circuitCode=jt&player1Id={player_id}"})
            
            response = sessao.get(url_api, timeout=10)
            
            # Checagem 1: Bloqueio escancarado
            if "Incapsula" in response.text or response.status_code != 200:
                ultimo_erro = f"Bloqueio explícito (Code {response.status_code})"
                print(f"  -> Bloqueado! Limpando os rastros e aguardando 5s...")
                
                # A MÁGICA AQUI: Apaga a memória em vez de destruir a conexão
                sessao.cookies.clear() 
                try:
                    sessao.get("https://www.itftennis.com/en/", timeout=10)
                except:
                    pass
                
                time.sleep(5)
                continue
                
            # Checagem 2: Bloqueio ninja (mandou HTML em vez de JSON)
            try:
                dados_json = response.json()
            except ValueError:
                ultimo_erro = "Bloqueio Ninja (Página em branco/HTML)"
                print(f"  -> Bloqueio Ninja! Limpando os rastros e aguardando 5s...")
                sessao.cookies.clear()
                try:
                    sessao.get("https://www.itftennis.com/en/", timeout=10)
                except:
                    pass
                time.sleep(5)
                continue

            # Se chegou aqui, pegou os dados!
            mao = dados_json.get('playHand') or 'Unknown'
            backhand = dados_json.get('backHandStyle') or 'Unknown'
            
            df.at[index, 'Play_Hand'] = mao
            df.at[index, 'Backhand'] = backhand
            
            print(f"[{index + 1}/{total_jogadores}] ID {player_id} -> {mao} | {backhand}")
            sucesso_req = True
            break 
            
        except requests.exceptions.RequestException as e:
            ultimo_erro = f"Erro de conexão ({str(e)[:40]})"
            print(f"  -> Falha de rede (Tentativa {tentativa}). Aguardando 5s...")
            time.sleep(5)
        except Exception as e:
            ultimo_erro = f"Erro genérico: {str(e)}"
            print(f"  -> Erro genérico (Tentativa {tentativa}). Aguardando 3s...")
            time.sleep(3)

    if not sucesso_req:
         print(f"[{index + 1}/{total_jogadores}] ID {player_id} -> ❌ Falha definitiva. Motivo: {ultimo_erro}")
         df.at[index, 'Play_Hand'] = 'Error'
         df.at[index, 'Backhand'] = 'Error'

    if (index + 1) % 20 == 0:
        df.to_csv(arquivo_enriquecido, index=False)

    time.sleep(random.uniform(1.5, 2.5))

df.to_csv(arquivo_enriquecido, index=False)
print("\n--- EXTRAÇÃO DE CARACTERÍSTICAS FÍSICAS CONCLUÍDA! ---")