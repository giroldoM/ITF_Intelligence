from curl_cffi import requests
import pandas as pd
import time
import os
import random

print("--- INICIANDO RASPAGEM: PARTIDAS DAS JOGADORAS PRINCIPAIS ---")

# Arquivos de entrada e saída
arquivo_jogadoras = "jogadoras_ids_top4000_enriched.csv"
arquivo_saida = "itf_matches_COMPLETO_RAW_W.csv"

# 1. Carregar a lista de Jogadoras
df_players = pd.read_csv(arquivo_jogadoras)
lista_ids = df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False).tolist()

total_jogadoras = len(lista_ids)
print(f"Total de jogadoras na base: {total_jogadoras}")

# 2. Sistema de Retomada (Resume)
todas_as_partidas = []
ids_ja_processados = set()

if os.path.exists(arquivo_saida):
    print("Ficheiro de progresso encontrado! A ler o que já foi extraído...")
    df_existente = pd.read_csv(arquivo_saida)
    todas_as_partidas = df_existente.to_dict('records')
    # Descobre quais IDs já estão no ficheiro guardado
    ids_ja_processados = set(df_existente['Player_ID'].astype(str).str.replace('.0', '', regex=False).unique())
    print(f"Já foram processadas {len(ids_ja_processados)} jogadoras. Faltam {total_jogadoras - len(ids_ja_processados)}.")

# 3. Preparando a Sessão Antibloqueio
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

print("A preparar o disfarce inicial...")
sessao = criar_nova_sessao()

# 4. O Loop de Extração
for i, player_id in enumerate(lista_ids, start=1):
    
    if player_id in ids_ja_processados:
        continue
        
    url_api = f"https://www.itftennis.com/tennis/api/PlayerApi/GetPlayerActivity?circuitCode=JT&matchTypeCode=S&playerId={player_id}&skip=0&surfaceCode=&take=1000&tourCategoryCode=&year="
    
    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = sessao.get(url_api, timeout=12)
            
            # Verificação de bloqueio do Incapsula
            if "Incapsula" in response.text or response.status_code != 200:
                sessao.cookies.clear()
                try: sessao.get("https://www.itftennis.com/en/", timeout=10)
                except: pass
                time.sleep(random.uniform(3.0, 5.0))
                continue
                
            # Verifica bloqueio Ninja (HTML em vez de JSON)
            try:
                dados_json = response.json()
            except ValueError:
                sessao.cookies.clear()
                try: sessao.get("https://www.itftennis.com/en/", timeout=10)
                except: pass
                time.sleep(random.uniform(3.0, 5.0))
                continue

            jogos_encontrados = 0
            for torneio in dados_json.get('items', []):
                nome_torneio = torneio.get('tournamentName')
                data_torneio = torneio.get('dates')
                superficie = torneio.get('surfaceDesc') 
                ano_torneio = data_torneio[-4:] if data_torneio else "Desconhecido"
                
                for evento in torneio.get('events', []):
                    for partida in evento.get('matches', []):
                        
                        # Ignorar W.O. e Byes logo na fonte
                        if partida.get('resultStatusCode') in ['BYE', 'WO'] or partida.get('resultCode') == 'B':
                            continue
                            
                        oponentes = partida.get('opponents', [])
                        if oponentes:
                            oponente_nome = f"{oponentes[0].get('givenName')} {oponentes[0].get('familyName')}"
                            oponente_id = oponentes[0].get('playerId')
                            oponente_nacionalidade = oponentes[0].get('nationality')
                        else:
                            oponente_nome, oponente_id, oponente_nacionalidade = "Desconhecido", None, None
                        
                        placar = ""
                        for set_score in partida.get('scores', []):
                            placar += f"{set_score.get('scoreOne')}-{set_score.get('scoreTwo')} "
                        
                        linha_partida = {
                            'Player_ID': player_id,
                            'Opponent_ID': oponente_id,
                            'Opponent_Name': oponente_nome,
                            'Opponent_Nation': oponente_nacionalidade,
                            'Tournament': nome_torneio,
                            'Year': ano_torneio,
                            'Date': data_torneio,
                            'Surface': superficie,
                            'Round': partida.get('roundGroup', {}).get('Value'),
                            'Result': partida.get('resultCode'),
                            'Score': placar.strip()
                        }
                        
                        todas_as_partidas.append(linha_partida)
                        jogos_encontrados += 1
            
            print(f"[{i}/{total_jogadoras}] Jogadora {player_id}: {jogos_encontrados} jogos extraídos.")
            ids_ja_processados.add(player_id)
            break # Sucesso, sai do loop de tentativas
            
        except Exception as e:
            time.sleep(3)

    # SISTEMA DE SEGURANÇA: Guardar a cada 50 jogadoras para não perder dados na RAM
    if len(ids_ja_processados) % 50 == 0:
        df_temp = pd.DataFrame(todas_as_partidas)
        df_temp.to_csv(arquivo_saida, index=False)

    time.sleep(random.uniform(1.0, 2.0))

# Salvamento Final
if todas_as_partidas:
    df_completo = pd.DataFrame(todas_as_partidas)
    df_completo.to_csv(arquivo_saida, index=False)
    print(f"\n--- SUCESSO! {len(df_completo)} partidas extraídas e guardadas em '{arquivo_saida}' ---")
else:
    print("\n--- Nenhuma partida nova foi extraída. ---")