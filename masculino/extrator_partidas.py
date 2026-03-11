from curl_cffi import requests
import pandas as pd
import time
import os

# 1. Lendo os IDs do arquivo que você acabou de gerar
arquivo_ids = "jogadores_ids_top4000.csv"
print(f"Lendo arquivo de jogadores: {arquivo_ids}")
df_jogadores = pd.read_csv(arquivo_ids)

# Transforma a coluna de IDs numa lista do Python
lista_ids = df_jogadores['Player_ID'].astype(str).tolist()
total_jogadores = len(lista_ids)

url_porta_da_frente = "https://www.itftennis.com/en/"
print("Preparando o disfarce de navegador...")
sessao = requests.Session(impersonate="chrome120")

print("Pegando os cookies de acesso na página inicial...")
try:
    sessao.get(url_porta_da_frente, timeout=15)
except:
    pass # Ignora se der erro de DNS rápido aqui, a API resolve depois

todas_as_partidas = []
arquivo_backup = "backup_partidas_brutas.csv"

print(f"\nINICIANDO EXTRAÇÃO DE {total_jogadores} JOGADORES...")
print("Isso vai levar cerca de 2h a 2h30. Pode ir tomar um café!\n")

for i, player_id in enumerate(lista_ids, start=1):
    
    url_api = f"https://www.itftennis.com/tennis/api/PlayerApi/GetPlayerActivity?circuitCode=JT&matchTypeCode=S&playerId={player_id}&skip=0&surfaceCode=&take=1000&tourCategoryCode=&year="
    
    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = sessao.get(url_api, timeout=15)
            
            if "Incapsula" in response.text:
                if tentativa == max_tentativas:
                    print(f"[{i}/{total_jogadores}] Jogador {player_id}: Bloqueado pelo Incapsula. Pulando.")
                time.sleep(3)
                continue
                
            dados_json = response.json()
            jogos_encontrados = 0

            for torneio in dados_json.get('items', []):
                nome_torneio = torneio.get('tournamentName')
                data_torneio = torneio.get('dates')
                superficie = torneio.get('surfaceDesc') 
                ano_torneio = data_torneio[-4:] if data_torneio else "Desconhecido"
                
                for evento in torneio.get('events', []):
                    for partida in evento.get('matches', []):
                        
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
            
            print(f"[{i}/{total_jogadores}] Jogador {player_id}: {jogos_encontrados} jogos extraídos.")
            break # Sai do loop de tentativa porque deu certo
            
        except Exception as e:
            if tentativa == max_tentativas:
                print(f"[{i}/{total_jogadores}] Jogador {player_id}: Erro final ({e}). Pulando.")
            time.sleep(3)

    # SISTEMA DE SALVAMENTO DE SEGURANÇA (A CADA 100 JOGADORES)
    if i % 100 == 0:
        df_temp = pd.DataFrame(todas_as_partidas)
        df_temp.to_csv(arquivo_backup, index=False)
        print(f">>> CHECKPOINT: Backup salvo com {len(df_temp)} partidas totais até agora.")

    # A Pausa de 2 segundos para não derrubar o servidor e não sermos bloqueados
    time.sleep(2)

# --- FASE FINAL: SEPARAR POR ANO ---
print("\n--- RASPAGEM CONCLUÍDA COM SUCESSO! ---")
df_completo = pd.DataFrame(todas_as_partidas)
print(f"Grand Total: {len(df_completo)} jogos extraídos de {total_jogadores} jogadores.")

# Salva um backup final completo
df_completo.to_csv("itf_matches_COMPLETO_RAW.csv", index=False)

# Separando em arquivos por ano
anos_disponiveis = df_completo['Year'].unique()

print("\nGerando os arquivos finais divididos por ano:")
for ano in anos_disponiveis:
    if ano == "Desconhecido":
        continue
        
    df_ano = df_completo[df_completo['Year'] == ano]
    nome_arquivo = f"itf_matches_{ano}.csv"
    df_ano.to_csv(nome_arquivo, index=False)
    print(f" -> {nome_arquivo} salvo com {len(df_ano)} partidas.")

# Opcional: Apagar o arquivo de backup intermediário já que terminou
if os.path.exists(arquivo_backup):
    os.remove(arquivo_backup)
    print("Arquivo de backup temporário limpo.")