import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import xgboost as xgb

class MotorInteligencia:
    def __init__(self, chave='M'):
        self.chave = chave
        
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        raiz_projeto = os.path.abspath(os.path.join(diretorio_atual, '..'))
        
        # Guardamos a pasta na classe para usar depois no carregamento do modelo XGBoost
        self.pasta_dados = os.path.join(raiz_projeto, 'masculino') if chave == 'M' else os.path.join(raiz_projeto, 'feminino')
        
        print(f"[{chave}] Carregando dados para inteligencia de negocio a partir de: {self.pasta_dados}")
        self.df_players = pd.read_csv(os.path.join(self.pasta_dados, f"dim_players_{chave}.csv"))
        self.df_matches = pd.read_csv(os.path.join(self.pasta_dados, f"fact_matches_with_elo_{chave}.csv"))
        
        self.df_players['Player_ID'] = self.df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['winner_id'] = self.df_matches['winner_id'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['loser_id'] = self.df_matches['loser_id'].astype(str).str.replace('.0', '', regex=False)
        
        self.df_matches['Tourney_Date'] = pd.to_datetime(self.df_matches['Tourney_Date'])
        
        self._calcular_elos_atuais()

    def _obter_ultimos_elos(self, df, col_w, col_l):
        df_w = df[['Tourney_Date', 'winner_id', col_w]].rename(columns={'winner_id': 'Player_ID', col_w: 'Elo'})
        df_l = df[['Tourney_Date', 'loser_id', col_l]].rename(columns={'loser_id': 'Player_ID', col_l: 'Elo'})
        df_all = pd.concat([df_w, df_l]).sort_values('Tourney_Date')
        return df_all.drop_duplicates(subset=['Player_ID'], keep='last').copy()

    def _calcular_elos_atuais(self):
        self.elos_atuais = self._obter_ultimos_elos(self.df_matches, 'Winner_Global_Elo', 'Loser_Global_Elo')
        
        matches_clay = self.df_matches[self.df_matches['Surface'] == 'Clay']
        self.elos_clay = self._obter_ultimos_elos(matches_clay, 'Winner_Surface_Elo', 'Loser_Surface_Elo')
        
        matches_hard = self.df_matches[self.df_matches['Surface'] == 'Hard']
        self.elos_hard = self._obter_ultimos_elos(matches_hard, 'Winner_Surface_Elo', 'Loser_Surface_Elo')

        matches_grass = self.df_matches[self.df_matches['Surface'] == 'Grass']
        self.elos_grass = self._obter_ultimos_elos(matches_grass, 'Winner_Surface_Elo', 'Loser_Surface_Elo')
        
        self.elos_atuais['Player_ID'] = self.elos_atuais['Player_ID'].astype(str)
        self.df_players['Player_ID'] = self.df_players['Player_ID'].astype(str)
        
        self.elos_atuais = self.elos_atuais.merge(
            self.df_players[['Player_ID', 'Birth_Year', 'Name', 'Nationality']], 
            on='Player_ID', how='left'
        )

    def gerar_raio_x_jogador(self, player_id):
        player_id = str(player_id)
        info = self.df_players[self.df_players['Player_ID'] == player_id]
        if info.empty:
            return {"erro": "Jogador nao encontrado."}
        
        nome = info.iloc[0]['Name']
        nacionalidade = info.iloc[0]['Nationality']
        ano_nasc = info.iloc[0]['Birth_Year']
        mao_dominante = info.iloc[0].get('Hand', 'U')
        if pd.isna(mao_dominante) or mao_dominante == 'U': mao_dominante = "Destro/Canhoto (N/A)"
        elif mao_dominante == 'R': mao_dominante = "Destro"
        elif mao_dominante == 'L': mao_dominante = "Canhoto"

        idade_aprox = datetime.now().year - int(ano_nasc) if pd.notna(ano_nasc) else "N/A"

        jogos_w = self.df_matches[self.df_matches['winner_id'] == player_id].copy()
        jogos_l = self.df_matches[self.df_matches['loser_id'] == player_id].copy()
        
        if not jogos_w.empty:
            jogos_w['Meu_Elo'] = jogos_w['Winner_Global_Elo']
            jogos_w['Meu_Elo_Surface'] = jogos_w['Winner_Surface_Elo']
            jogos_w['Opponent_Elo'] = jogos_w['Loser_Global_Elo']
            jogos_w['Resultado'] = 'W'
            
        if not jogos_l.empty:
            jogos_l['Meu_Elo'] = jogos_l['Loser_Global_Elo']
            jogos_l['Meu_Elo_Surface'] = jogos_l['Loser_Surface_Elo']
            jogos_l['Opponent_Elo'] = jogos_l['Winner_Global_Elo']
            jogos_l['Resultado'] = 'L'
        
        historico = pd.concat([jogos_w, jogos_l]).sort_values('Tourney_Date')
        if historico.empty:
            return {"nome": nome, "erro": "Sem historico de partidas."}

        elo_atual = historico.iloc[-1]['Meu_Elo']
        rank_global = (self.elos_atuais['Elo'] > elo_atual).sum() + 1
        total_jogadores = len(self.elos_atuais)
        
        percentil = 0
        media_idade, std_idade = 1500.0, 100.0
        if pd.notna(ano_nasc):
            concorrentes = self.elos_atuais[self.elos_atuais['Birth_Year'] == ano_nasc]
            rank_na_idade = (concorrentes['Elo'] > elo_atual).sum() + 1
            total_concorrentes = len(concorrentes)
            if total_concorrentes > 0:
                percentil = 100 - ((rank_na_idade / total_concorrentes) * 100)
                percentil_str = f"Top {100 - percentil:.1f}%" if percentil > 50 else f"Bottom {percentil:.1f}%"
                media_idade = concorrentes['Elo'].mean()
                std_idade = concorrentes['Elo'].std()
            else:
                percentil_str = "N/A"
        else:
            rank_na_idade, total_concorrentes, percentil_str = "N/A", "N/A", "N/A"

        saibro = historico[historico['Surface'] == 'Clay']
        piso_duro = historico[historico['Surface'] == 'Hard']
        grama = historico[historico['Surface'] == 'Grass']
        
        elo_saibro = saibro.iloc[-1]['Meu_Elo_Surface'] if not saibro.empty else 1500
        elo_hard = piso_duro.iloc[-1]['Meu_Elo_Surface'] if not piso_duro.empty else 1500
        elo_grass = grama.iloc[-1]['Meu_Elo_Surface'] if not grama.empty else 1500
        
        rank_clay = (self.elos_clay['Elo'] > elo_saibro).sum() + 1 if not self.elos_clay.empty else "N/A"
        rank_hard = (self.elos_hard['Elo'] > elo_hard).sum() + 1 if not self.elos_hard.empty else "N/A"
        rank_grass = (self.elos_grass['Elo'] > elo_grass).sum() + 1 if not self.elos_grass.empty else "N/A"

        superficies_elos = {'Saibro': elo_saibro, 'Piso Duro': elo_hard, 'Grama': elo_grass}
        melhor_piso = max(superficies_elos, key=superficies_elos.get)
        pior_piso = min(superficies_elos, key=superficies_elos.get)
        
        if superficies_elos[melhor_piso] - superficies_elos[pior_piso] > 150:
            tag_superficie = f"Especialista em {melhor_piso}"
        else:
            tag_superficie = "Perfil Versatil"

        data_atual = historico['Tourney_Date'].max()
        historico_6m = historico[historico['Tourney_Date'] >= (data_atual - timedelta(days=180))]
        
        delta_6_meses = elo_atual - (historico.iloc[-len(historico_6m)-1]['Meu_Elo'] if len(historico) > len(historico_6m) else 1500)
        vitorias_6m = len(historico_6m[historico_6m['Resultado'] == 'W'])
        derrotas_6m = len(historico_6m[historico_6m['Resultado'] == 'L'])
        oponentes_media_6m = historico_6m['Opponent_Elo'].mean() if not historico_6m.empty else 0

        txt_momento = "em forte ascensao" if delta_6_meses > 40 else "em fase de estabilizacao" if delta_6_meses > -20 else "enfrentando oscilacoes"
        txt_elite = "acima da media da sua geracao" if percentil >= 75 else "dentro da media da sua idade"
        headline = f"Jogador {txt_momento}, {txt_elite}, com forte aptidao para {melhor_piso}."

        bullet_idade = f"Posicionamento: Atualmente no {percentil_str} mundial entre os nascidos em {int(ano_nasc) if pd.notna(ano_nasc) else 'N/A'}. {'Demonstra alto potencial de projecao.' if percentil >= 85 else 'Requer ganhos marginais para atingir a elite da categoria.'}"
        bullet_piso = f"Perfil Competitivo: O diferencial entre o melhor e o pior piso indica um {tag_superficie.lower()}. O rating no {melhor_piso} e o seu principal trunfo."
        
        txt_oponente = "adversarios de alto nivel" if oponentes_media_6m > media_idade else "adversarios de nivel mediano/inferior"
        bullet_forma = f"Momento Recente: Nos ultimos 6 meses, regista um recorde de {vitorias_6m}V - {derrotas_6m}D. Tem enfrentado {txt_oponente} (Elo Medio: {round(oponentes_media_6m)}), resultando num delta de {round(delta_6_meses)} pontos."

        return {
            "id": player_id,
            "nome": nome,
            "nacionalidade": nacionalidade,
            "idade": idade_aprox,
            "ano_nasc": int(ano_nasc) if pd.notna(ano_nasc) else "Desconhecido",
            "mao_dominante": mao_dominante,
            
            "headline": headline,
            "bullet_idade": bullet_idade,
            "bullet_piso": bullet_piso,
            "bullet_forma": bullet_forma,
            
            "elo_global_atual": round(elo_atual),
            "ranking_global": f"{rank_global} de {total_jogadores}",
            
            "elo_saibro": round(elo_saibro),
            "ranking_saibro": rank_clay,
            "elo_hard": round(elo_hard),
            "ranking_hard": rank_hard,
            "elo_grass": round(elo_grass),
            "ranking_grass": rank_grass,
            "tag_superficie": tag_superficie,
            "melhor_piso": melhor_piso,
            
            "vitorias_6m": vitorias_6m,
            "derrotas_6m": derrotas_6m,
            "oponentes_media_6m": round(oponentes_media_6m),
            "delta_6_meses": round(delta_6_meses),
            
            "percentil_idade": percentil_str,
            "ranking_idade": f"{rank_na_idade} de {total_concorrentes}",
            "gaussiana_media_idade": round(media_idade, 2),
            "gaussiana_std_idade": round(std_idade, 2),
            
            "historico_completo": historico[['Tourney_Date', 'Surface', 'Meu_Elo', 'Meu_Elo_Surface', 'Resultado']]
        }

    def simular_confronto_ia(self, id_jogador_a, id_jogador_b, superficie='Saibro'):
        """
        Calcula as variaveis em tempo real e pede a probabilidade ao modelo guardado.
        Superficies aceitas: 'Saibro', 'Piso Duro', 'Grama'.
        """
        # 1. Puxar dados completos dos dois atletas
        raio_a = self.gerar_raio_x_jogador(id_jogador_a)
        raio_b = self.gerar_raio_x_jogador(id_jogador_b)
        
        if "erro" in raio_a or "erro" in raio_b:
            return {"erro": "Um dos IDs fornecidos nao foi encontrado."}

        # 2. Calcular as Features exatas
        elo_diff = raio_a['elo_global_atual'] - raio_b['elo_global_atual']
        
        mapa_superficie = {'Saibro': 'elo_saibro', 'Piso Duro': 'elo_hard', 'Grama': 'elo_grass'}
        chave_sup = mapa_superficie.get(superficie, 'elo_saibro')
        surface_elo_diff = raio_a[chave_sup] - raio_b[chave_sup]
        
        idade_a = raio_a['idade'] if raio_a['idade'] != "N/A" else 18
        idade_b = raio_b['idade'] if raio_b['idade'] != "N/A" else 18
        age_diff = idade_a - idade_b

        df_simulacao = pd.DataFrame({
            'elo_diff': [elo_diff],
            'surface_elo_diff': [surface_elo_diff],
            'age_diff': [age_diff]
        })

        # 3. Carregar IA e Simular
        caminho_modelo = os.path.join(self.pasta_dados, f"xgb_model_{self.chave}.json")
        if not os.path.exists(caminho_modelo):
            return {"erro": f"Ficheiro de modelo nao encontrado: {caminho_modelo}"}
            
        modelo_ia = xgb.XGBClassifier()
        modelo_ia.load_model(caminho_modelo)
        
        # O [0][1] pega exatamente a probabilidade da classe 1 (Vitoria do Jogador A)
        prob_a = modelo_ia.predict_proba(df_simulacao)[0][1]
        
        rreturn {
            "jogador_a": raio_a['nome'],
            "jogador_b": raio_b['nome'],
            "superficie": superficie,
            "probabilidade_vitoria_a": round(prob_a * 100, 2), # <-- Mudou para 2
            "probabilidade_vitoria_b": round((1 - prob_a) * 100, 2) # <-- Mudou para 2
        }
        

if __name__ == "__main__":
    motor = MotorInteligencia(chave='W')
    
    # ID da Victoria Barros
    id_cliente = "800655335" 
    
    #\
    # Pode substituir pelo ID real dela ou de outra se este nao constar na sua base.
    id_adversaria = "800591535"
    
    print("\n--- SIMULADOR DE HEAD-TO-HEAD (XGBOOST) ---")
    resultado = motor.simular_confronto_ia(id_cliente, id_adversaria, superficie='Piso Duro')
    
    if "erro" in resultado:
        print(f"Erro na simulacao: {resultado['erro']}")
    else:
        print(f"Matchup: {resultado['jogador_a']} vs {resultado['jogador_b']} ({resultado['superficie']})")
        print(f"Probabilidade de {resultado['jogador_a']}: {resultado['probabilidade_vitoria_a']:.2f}%")
        print(f"Probabilidade de {resultado['jogador_b']}: {resultado['probabilidade_vitoria_b']:.2f}%")