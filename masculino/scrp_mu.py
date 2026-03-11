from curl_cffi import requests
import pandas as pd

player_id = "800680259"

# A página inicial só para pegar os cookies de segurança
url_porta_da_frente = "https://www.itftennis.com/en/"
# O link da API com o ouro
url_api = f"https://www.itftennis.com/tennis/api/PlayerApi/GetPlayerActivity?circuitCode=JT&matchTypeCode=S&playerId={player_id}&skip=0&surfaceCode=&take=1000&tourCategoryCode=&year="

print("Preparando o disfarce de navegador...")

# O 'impersonate' faz o script se comportar em baixo nível exatamente como o Chrome 120
sessao = requests.Session(impersonate="chrome120")

# 1. Pegando o "crachá" de visitante normal
print("Passo 1: Entrando de mansinho na página inicial para pegar os cookies de acesso...")
sessao.get(url_porta_da_frente)

# 2. Indo direto na API agora que estamos liberados
print("Passo 2: Puxando os dados da API...")
response = sessao.get(url_api)

# Verificando se o bloqueio do Incapsula sumiu
if "Incapsula" in response.text:
    print("Opa, o Incapsula ainda nos pegou. Precisaremos de um plano C.")
else:
    try:
        dados_json = response.json()
        partidas_limpas = []

        for torneio in dados_json.get('items', []):
            nome_torneio = torneio.get('tournamentName')
            data_torneio = torneio.get('dates')
            superficie = torneio.get('surfaceDesc') 
            
            for evento in torneio.get('events', []):
                for partida in evento.get('matches', []):
                    
                    # Filtra os BYEs e Walkovers que sujam o rating Elo
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
                        'Date': data_torneio,
                        'Surface': superficie,
                        'Round': partida.get('roundGroup', {}).get('Value'),
                        'Result': partida.get('resultCode'),
                        'Score': placar.strip()
                    }
                    
                    partidas_limpas.append(linha_partida)

        df = pd.DataFrame(partidas_limpas)
        print(f"\nSUCESSO! Total de jogos válidos extraídos: {len(df)}")
        print("-" * 50)
        print(df.head())
        
        # Descomente a linha abaixo quando for salvar o arquivo definitivo!
        df.to_csv(f"itf_matches_{player_id}.csv", index=False)

    except Exception as e:
        print(f"Erro ao processar os dados: {e}")