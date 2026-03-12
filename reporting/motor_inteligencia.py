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
        
        self.pasta_dados = os.path.join(raiz_projeto, 'masculino') if chave == 'M' else os.path.join(raiz_projeto, 'feminino')
        
        print(f"[{chave}] Carregando dados para inteligencia de negocio a partir de: {self.pasta_dados}")
        
        # --- LÓGICA DE NOMES DE ARQUIVOS ADAPTÁVEL ---
        if chave == 'M':
            arquivo_players = "dim_players.csv"
            arquivo_matches = "fact_matches_with_elo.csv"
            arquivo_ativos = "jogadores_ids_top4000_enriched.csv"
        else:
            arquivo_players = "dim_players_W.csv"
            arquivo_matches = "fact_matches_with_elo_W.csv"
            arquivo_ativos = "jogadoras_ids_top4000_enriched.csv"
            
        self.df_players = pd.read_csv(os.path.join(self.pasta_dados, arquivo_players))
        self.df_matches = pd.read_csv(os.path.join(self.pasta_dados, arquivo_matches))
        # ---------------------------------------------
        
        self.df_players['Player_ID'] = self.df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['winner_id'] = self.df_matches['winner_id'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['loser_id'] = self.df_matches['loser_id'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['Tourney_Date'] = pd.to_datetime(self.df_matches['Tourney_Date'])
        
        # Filtro de Ativos (Top 4000)
        caminho_ativos = os.path.join(self.pasta_dados, arquivo_ativos)
        
        if os.path.exists(caminho_ativos):
            df_ativos = pd.read_csv(caminho_ativos)
            col_id = 'Player_ID' if 'Player_ID' in df_ativos.columns else df_ativos.columns[0]
            self.lista_ativos = df_ativos[col_id].astype(str).str.replace('.0', '', regex=False).tolist()
            print(f"[{chave}] Filtro de Ativos ativado: {len(self.lista_ativos)} jogadores no ranking oficial.")
        else:
            print(f"[{chave}] AVISO: {arquivo_ativos} nao encontrado. Ranquando contra toda a base historica.")
            self.lista_ativos = None

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
        if info.empty: return {"erro": "Jogador não encontrado."}
        
        nome = info.iloc[0]['Name']
        nacionalidade = info.iloc[0]['Nationality']
        ano_nasc = info.iloc[0]['Birth_Year']
        idade_aprox = datetime.now().year - int(ano_nasc) if pd.notna(ano_nasc) else "N/A"
        
        # Logica limpa para a Mao Dominante
        mao_dominante = info.iloc[0].get('Hand', 'U')
        str_mao = ""
        if pd.notna(mao_dominante) and mao_dominante in ['R', 'L']:
            if mao_dominante == 'R':
                str_mao = " &middot; Mão: Destra" if self.chave == 'W' else " &middot; Mão: Destro"
            else:
                str_mao = " &middot; Mão: Canhota" if self.chave == 'W' else " &middot; Mão: Canhoto"
                
        linha_meta = f"{nacionalidade} &middot; {idade_aprox} anos ({int(ano_nasc) if pd.notna(ano_nasc) else 'N/A'}){str_mao}"

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
        if historico.empty: return {"nome": nome, "erro": "Sem histórico de partidas."}

        elo_atual = historico.iloc[-1]['Meu_Elo']
        
        if self.lista_ativos:
            concorrentes_ativos = self.elos_atuais[self.elos_atuais['Player_ID'].isin(self.lista_ativos)]
        else:
            concorrentes_ativos = self.elos_atuais
            
        rank_global = (concorrentes_ativos['Elo'] > elo_atual).sum() + 1
        total_jogadores = len(concorrentes_ativos)
        
        percentil = 0
        media_idade, std_idade = 1500.0, 100.0
        if pd.notna(ano_nasc):
            concorrentes_idade = concorrentes_ativos[concorrentes_ativos['Birth_Year'] == ano_nasc]
            rank_na_idade = (concorrentes_idade['Elo'] > elo_atual).sum() + 1
            total_concorrentes = len(concorrentes_idade)
            
            if total_concorrentes > 0:
                percentil = 100 - ((rank_na_idade / total_concorrentes) * 100)
                percentil_str = f"Top {100 - percentil:.1f}%" if percentil > 50 else f"Bottom {percentil:.1f}%"
                media_idade = concorrentes_idade['Elo'].mean()
                std_idade = concorrentes_idade['Elo'].std()
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
            tag_superficie = "Perfil Versátil"

        data_atual = historico['Tourney_Date'].max()
        historico_6m = historico[historico['Tourney_Date'] >= (data_atual - timedelta(days=180))]
        
        delta_6_meses = elo_atual - (historico.iloc[-len(historico_6m)-1]['Meu_Elo'] if len(historico) > len(historico_6m) else 1500)
        vitorias_6m = len(historico_6m[historico_6m['Resultado'] == 'W'])
        derrotas_6m = len(historico_6m[historico_6m['Resultado'] == 'L'])
        oponentes_media_6m = historico_6m['Opponent_Elo'].mean() if not historico_6m.empty else 0

        txt_momento = "em forte ascensão" if delta_6_meses > 40 else "em fase de estabilização" if delta_6_meses > -20 else "enfrentando oscilações"
        txt_elite = "acima da média da sua geração" if percentil >= 75 else "dentro da média da sua idade"
        headline = f"Jogador(a) {txt_momento}, {txt_elite}, com forte aptidão para {melhor_piso}."

        bullet_idade = f"Posicionamento: Atualmente no {percentil_str} mundial entre os nascidos em {int(ano_nasc) if pd.notna(ano_nasc) else 'N/A'}. {'Demonstra alto potencial de projeção.' if percentil >= 85 else 'Requer ganhos marginais para atingir a elite da categoria.'}"
        bullet_piso = f"Perfil Competitivo: O diferencial entre o melhor e o pior piso indica um {tag_superficie.lower()}. O rating no {melhor_piso} é o principal trunfo."
        
        txt_oponente = "adversários de alto nível" if oponentes_media_6m > media_idade else "adversários de nível mediano/inferior"
        bullet_forma = f"Momento Recente: Nos últimos 6 meses, regista um recorde de {vitorias_6m}V - {derrotas_6m}D. Tem enfrentado {txt_oponente} (Elo Médio: {round(oponentes_media_6m)}), resultando num delta de {round(delta_6_meses)} pontos."

        return {
            "id": player_id,
            "nome": nome,
            "linha_meta": linha_meta,
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

    def buscar_adversarios_dinamicos(self, player_id, dados_scout):
        """Seleciona 3 adversários reais baseados nas regras de negocio B2B."""
        adversarios = []
        ano_nasc = dados_scout.get('ano_nasc')
        elo_global = dados_scout['elo_global_atual']
        melhor_piso = dados_scout['melhor_piso']

        # Filtrar apenas ativos (excluindo o proprio jogador)
        if self.lista_ativos:
            pool = self.elos_atuais[(self.elos_atuais['Player_ID'].isin(self.lista_ativos)) & (self.elos_atuais['Player_ID'] != player_id)].copy()
        else:
            pool = self.elos_atuais[self.elos_atuais['Player_ID'] != player_id].copy()

        if pool.empty: return []

        # 1. O Numero 1 da mesma idade (Quadra Dura)
        pool_hard = pool.merge(self.elos_hard[['Player_ID', 'Elo']], on='Player_ID', how='left', suffixes=('', '_hard'))
        pool_mesma_idade = pool_hard[pool_hard['Birth_Year'] == ano_nasc].sort_values(by='Elo_hard', ascending=False)
        if not pool_mesma_idade.empty:
            adv_1 = pool_mesma_idade.iloc[0]
            adversarios.append({
                "id": str(adv_1['Player_ID']), "piso": "Piso Duro",
                "contexto": f"#1 da Geracao {ano_nasc} (Piso Duro)"
            })

        # 2. O Alvo de Ranking (10 posicoes acima no Global)
        acima_global = pool[pool['Elo'] > elo_global].sort_values(by='Elo', ascending=True)
        if not acima_global.empty:
            idx = min(9, len(acima_global) - 1) # Pega o 10o cara acima
            adv_2 = acima_global.iloc[idx]
            adversarios.append({
                "id": str(adv_2['Player_ID']), "piso": melhor_piso,
                "contexto": f"Alvo Direto (+10 posicoes no Global)"
            })

        # 3. O Rival de Superficie (Especialista um pouco acima no mesmo piso favorito)
        mapa_dfs = {'Saibro': self.elos_clay, 'Piso Duro': self.elos_hard, 'Grama': self.elos_grass}
        df_sup = mapa_dfs.get(melhor_piso)
        if df_sup is not None and not df_sup.empty:
            chave_elo_sup = 'elo_saibro' if melhor_piso == 'Saibro' else 'elo_hard' if melhor_piso == 'Piso Duro' else 'elo_grass'
            meu_elo_sup = dados_scout.get(chave_elo_sup, 1500)
            
            pool_sup = df_sup[(df_sup['Player_ID'].isin(pool['Player_ID'])) & (df_sup['Elo'] > meu_elo_sup)].sort_values(by='Elo', ascending=True)
            if not pool_sup.empty:
                idx_sup = min(4, len(pool_sup) - 1) # ~5 posicoes acima neste piso
                adv_3 = pool_sup.iloc[idx_sup]
                adversarios.append({
                    "id": str(adv_3['Player_ID']), "piso": melhor_piso,
                    "contexto": f"Rival Proximo ({melhor_piso})"
                })

        return adversarios

    def simular_confronto_ia(self, id_jogador_a, id_jogador_b, superficie='Saibro'):
        raio_a = self.gerar_raio_x_jogador(id_jogador_a)
        raio_b = self.gerar_raio_x_jogador(id_jogador_b)
        
        if "erro" in raio_a or "erro" in raio_b: return {"erro": "Um dos IDs nao foi encontrado."}

        elo_diff = raio_a['elo_global_atual'] - raio_b['elo_global_atual']
        mapa_superficie = {'Saibro': 'elo_saibro', 'Piso Duro': 'elo_hard', 'Grama': 'elo_grass'}
        chave_sup = mapa_superficie.get(superficie, 'elo_saibro')
        surface_elo_diff = raio_a[chave_sup] - raio_b[chave_sup]
        
        idade_a = raio_a['idade'] if raio_a['idade'] != "N/A" else 18
        idade_b = raio_b['idade'] if raio_b['idade'] != "N/A" else 18
        age_diff = idade_a - idade_b

        df_simulacao = pd.DataFrame({'elo_diff': [elo_diff], 'surface_elo_diff': [surface_elo_diff], 'age_diff': [age_diff]})

        caminho_modelo = os.path.join(self.pasta_dados, f"xgb_model_{self.chave}.json")
        if not os.path.exists(caminho_modelo): return {"erro": f"Ficheiro de modelo nao encontrado: {caminho_modelo}"}
            
        modelo_ia = xgb.XGBClassifier()
        modelo_ia.load_model(caminho_modelo)
        
        prob_a = modelo_ia.predict_proba(df_simulacao)[0][1]
        
        return {
            "jogador_a": raio_a['nome'],
            "jogador_b": raio_b['nome'],
            "superficie": superficie,
            "probabilidade_vitoria_a": round(prob_a * 100, 2),
            "probabilidade_vitoria_b": round((1 - prob_a) * 100, 2)
        }