from curl_cffi import requests
import pandas as pd
import time

url_ranking = "https://www.itftennis.com/tennis/api/PlayerRankApi/GetPlayerRankings?circuitCode=JT&playerTypeCode=B&ageCategoryCode=&juniorRankingType=itf&take=4000&skip=0&isOrderAscending=true"
url_porta_da_frente = "https://www.itftennis.com/en/"

print("Preparando o disfarce de navegador...")
sessao = requests.Session(impersonate="chrome120")

max_tentativas = 3
sucesso = False

for tentativa in range(1, max_tentativas + 1):
    try:
        print(f"\n--- Tentativa {tentativa} de {max_tentativas} ---")
        print("Pegando os cookies de acesso na página inicial...")
        sessao.get(url_porta_da_frente, timeout=15)
        
        print("Acessando a API de Rankings...")
        response = sessao.get(url_ranking, timeout=20)
        
        if "Incapsula" in response.text:
            print("Bloqueado pelo Incapsula. Retentando...")
            time.sleep(3)
            continue
            
        dados_json = response.json()
        lista_jogadores = []
        
        print("Processando a lista de jogadores...")
        for jogador in dados_json.get('items', []):
            info = {
                'Rank': jogador.get('rank'),
                'Player_ID': str(jogador.get('playerId')),
                'Name': f"{jogador.get('playerGivenName')} {jogador.get('playerFamilyName')}",
                'Nationality': jogador.get('playerNationalityCode'),
                'Birth_Year': jogador.get('birthYear') # <--- OLHA A MÁGICA AQUI!
            }
            lista_jogadores.append(info)
            
        df_ranking = pd.DataFrame(lista_jogadores)
        df_ranking = df_ranking.sort_values(by='Rank')
        
        nome_arquivo_ids = "jogadores_ids_top4000.csv"
        df_ranking.to_csv(nome_arquivo_ids, index=False)
        
        print(f"\nSUCESSO ESPETACULAR! Extraídos {len(df_ranking)} IDs de jogadores.")
        print(f"Lista salva no arquivo: {nome_arquivo_ids}")
        print("\nPrimeiros 5 jogadores da lista:")
        print(df_ranking.head())
        
        sucesso = True
        break 
        
    except ValueError:
        print("Erro: O servidor devolveu HTML. Retentando...")
        time.sleep(3)
    except Exception as e:
        print(f"Erro de rede: {e}. Retentando em 3 segundos...")
        time.sleep(3)

if not sucesso:
    print("\nFalha após todas as tentativas.")