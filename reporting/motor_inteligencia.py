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
        
        print(f"[{chave}] Carregando dados para inteligencia de negocio...")
        
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
        
        self.df_players['Player_ID'] = self.df_players['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['winner_id'] = self.df_matches['winner_id'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['loser_id'] = self.df_matches['loser_id'].astype(str).str.replace('.0', '', regex=False)
        self.df_matches['Tourney_Date'] = pd.to_datetime(self.df_matches['Tourney_Date'])
        
        # 1. Filtro de Ativos e Captura do RANKING ITF OFICIAL
        caminho_ativos = os.path.join(self.pasta_dados, arquivo_ativos)
        self.dict_ranks_itf = {}
        
        if os.path.exists(caminho_ativos):
            df_ativos = pd.read_csv(caminho_ativos)
            col_id = 'Player_ID' if 'Player_ID' in df_ativos.columns else df_ativos.columns[0]
            df_ativos[col_id] = df_ativos[col_id].astype(str).str.replace('.0', '', regex=False)
            self.lista_ativos = df_ativos[col_id].tolist()
            
            # Buscar a coluna Rank (tentar pelo nome 'Rank' ou pelos indices passados)
            if 'Rank' in df_ativos.columns:
                col_rank = 'Rank'
            else:
                col_rank = df_ativos.columns[1] if chave == 'M' else df_ativos.columns[3]
                
            self.dict_ranks_itf = dict(zip(df_ativos[col_id], df_ativos[col_rank]))
            print(f"[{chave}] Ativos carregados: {len(self.lista_ativos)} | Rankings ITF mapeados.")
        else:
            print(f"[{chave}] AVISO: {arquivo_ativos} nao encontrado. Usando base historica inteira.")
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
        
        # Anexar Birth_Year aos Elos para os calculos de media da geracao
        for df_elo in [self.elos_atuais, self.elos_clay, self.elos_hard, self.elos_grass]:
            df_elo['Player_ID'] = df_elo['Player_ID'].astype(str)
            
        self.df_players['Player_ID'] = self.df_players['Player_ID'].astype(str)
        player_info = self.df_players[['Player_ID', 'Birth_Year', 'Name', 'Nationality']]
        
        self.elos_atuais = self.elos_atuais.merge(player_info, on='Player_ID', how='left')
        self.elos_clay = self.elos_clay.merge(player_info[['Player_ID', 'Birth_Year']], on='Player_ID', how='left')
        self.elos_hard = self.elos_hard.merge(player_info[['Player_ID', 'Birth_Year']], on='Player_ID', how='left')
        self.elos_grass = self.elos_grass.merge(player_info[['Player_ID', 'Birth_Year']], on='Player_ID', how='left')

    def gerar_raio_x_jogador(self, player_id):
        player_id = str(player_id)
        info = self.df_players[self.df_players['Player_ID'] == player_id]
        if info.empty: return {"erro": "Jogador nao encontrado."}
        
        nome = info.iloc[0]['Name']
        nacionalidade = info.iloc[0]['Nationality']
        ano_nasc = info.iloc[0]['Birth_Year']
        idade_aprox = datetime.now().year - int(ano_nasc) if pd.notna(ano_nasc) else "N/A"
        
        # Puxar Rank Oficial ITF
        rank_itf = self.dict_ranks_itf.get(player_id, "N/A")
        if isinstance(rank_itf, float) and not np.isnan(rank_itf): rank_itf = int(rank_itf)
        
        mao_dominante = info.iloc[0].get('Hand', 'U')
        str_mao = ""
        if pd.notna(mao_dominante) and mao_dominante in ['R', 'L']:
            str_mao = " &middot; Mão: Destra" if (self.chave == 'W' and mao_dominante == 'R') else " &middot; Mão: Destro" if mao_dominante == 'R' else " &middot; Mão: Canhota" if self.chave == 'W' else " &middot; Mão: Canhoto"
                
        linha_meta = f"{nacionalidade} &middot; {idade_aprox} anos ({int(ano_nasc) if pd.notna(ano_nasc) else 'N/A'}){str_mao}"

        jogos_w = self.df_matches[self.df_matches['winner_id'] == player_id].copy()
        jogos_w['Meu_Elo'], jogos_w['Meu_Elo_Surface'], jogos_w['Opponent_Elo'], jogos_w['Resultado'] = jogos_w['Winner_Global_Elo'], jogos_w['Winner_Surface_Elo'], jogos_w['Loser_Global_Elo'], 'W'
        
        jogos_l = self.df_matches[self.df_matches['loser_id'] == player_id].copy()
        jogos_l['Meu_Elo'], jogos_l['Meu_Elo_Surface'], jogos_l['Opponent_Elo'], jogos_l['Resultado'] = jogos_l['Loser_Global_Elo'], jogos_l['Loser_Surface_Elo'], jogos_l['Winner_Global_Elo'], 'L'
        
        historico = pd.concat([jogos_w, jogos_l]).sort_values('Tourney_Date')
        if historico.empty: return {"nome": nome, "erro": "Sem historico de partidas."}

        elo_atual = historico.iloc[-1]['Meu_Elo']
        
        # Percentis
        if self.lista_ativos:
            concorrentes_ativos = self.elos_atuais[self.elos_atuais['Player_ID'].isin(self.lista_ativos)]
            ativos_clay = self.elos_clay[self.elos_clay['Player_ID'].isin(self.lista_ativos)]
            ativos_hard = self.elos_hard[self.elos_hard['Player_ID'].isin(self.lista_ativos)]
            ativos_grass = self.elos_grass[self.elos_grass['Player_ID'].isin(self.lista_ativos)]
        else:
            concorrentes_ativos, ativos_clay, ativos_hard, ativos_grass = self.elos_atuais, self.elos_clay, self.elos_hard, self.elos_grass
            
        rank_global_elo = (concorrentes_ativos['Elo'] > elo_atual).sum() + 1
        
        media_idade, std_idade = 1500.0, 100.0
        if pd.notna(ano_nasc):
            concorrentes_idade = concorrentes_ativos[concorrentes_ativos['Birth_Year'] == ano_nasc]
            rank_na_idade = (concorrentes_idade['Elo'] > elo_atual).sum() + 1
            if len(concorrentes_idade) > 0:
                percentil = 100 - ((rank_na_idade / len(concorrentes_idade)) * 100)
                percentil_str = f"Top {100 - percentil:.1f}%" if percentil > 50 else f"Bottom {percentil:.1f}%"
                media_idade, std_idade = concorrentes_idade['Elo'].mean(), concorrentes_idade['Elo'].std()
            else: percentil_str = "N/A"
            
            # Medias de Piso da Geracao
            med_clay_idade = ativos_clay[ativos_clay['Birth_Year'] == ano_nasc]['Elo'].mean()
            med_hard_idade = ativos_hard[ativos_hard['Birth_Year'] == ano_nasc]['Elo'].mean()
            med_grass_idade = ativos_grass[ativos_grass['Birth_Year'] == ano_nasc]['Elo'].mean()
        else:
            rank_na_idade, percentil_str = "N/A", "N/A"
            med_clay_idade = med_hard_idade = med_grass_idade = 1500.0

        saibro = historico[historico['Surface'] == 'Clay']
        piso_duro = historico[historico['Surface'] == 'Hard']
        grama = historico[historico['Surface'] == 'Grass']
        
        jogou_clay = not saibro.empty
        jogou_hard = not piso_duro.empty
        jogou_grass = not grama.empty

        elo_saibro = saibro.iloc[-1]['Meu_Elo_Surface'] if jogou_clay else 1500
        elo_hard = piso_duro.iloc[-1]['Meu_Elo_Surface'] if jogou_hard else 1500
        elo_grass = grama.iloc[-1]['Meu_Elo_Surface'] if jogou_grass else 1500
        
        # Formatar Diferencas (Ex: +150 ou -42)
        d_global = elo_atual - media_idade
        d_clay = elo_saibro - med_clay_idade
        d_hard = elo_hard - med_hard_idade
        d_grass = elo_grass - med_grass_idade
        
        str_diff_global = f"+{int(d_global)}" if d_global > 0 else f"{int(d_global)}"
        str_diff_clay = f"+{int(d_clay)}" if d_clay > 0 else f"{int(d_clay)}"
        str_diff_hard = f"+{int(d_hard)}" if d_hard > 0 else f"{int(d_hard)}"
        str_diff_grass = f"+{int(d_grass)}" if d_grass > 0 else f"{int(d_grass)}"

        rank_clay = (ativos_clay['Elo'] > elo_saibro).sum() + 1
        rank_hard = (ativos_hard['Elo'] > elo_hard).sum() + 1
        rank_grass = (ativos_grass['Elo'] > elo_grass).sum() + 1

        superficies_elos = {'Saibro': elo_saibro, 'Piso Duro': elo_hard, 'Grama': elo_grass}
        # Filtra apenas as superficies que o jogador realmente jogou para achar a melhor/pior
        superficies_jogadas = {k: v for k, v in superficies_elos.items() if (k == 'Saibro' and jogou_clay) or (k == 'Piso Duro' and jogou_hard) or (k == 'Grama' and jogou_grass)}
        
        if superficies_jogadas:
            melhor_piso = max(superficies_jogadas, key=superficies_jogadas.get)
            pior_piso = min(superficies_jogadas, key=superficies_jogadas.get)
            tag_superficie = f"Especialista em {melhor_piso}" if superficies_jogadas[melhor_piso] - superficies_jogadas[pior_piso] > 150 else "Perfil Versátil"
        else:
            melhor_piso = "N/A"
            tag_superficie = "Sem Dados de Piso"

        # Win Rate (Momentum)
        data_atual = historico['Tourney_Date'].max()
        historico_6m = historico[historico['Tourney_Date'] >= (data_atual - timedelta(days=180))]
        vitorias_6m = len(historico_6m[historico_6m['Resultado'] == 'W'])
        derrotas_6m = len(historico_6m[historico_6m['Resultado'] == 'L'])
        win_rate = (vitorias_6m / (vitorias_6m + derrotas_6m) * 100) if (vitorias_6m + derrotas_6m) > 0 else 0

        # Textos IA
        headline = f"Ranking #{rank_itf} mundial, no {percentil_str} da geração {int(ano_nasc) if pd.notna(ano_nasc) else ''}. Força primária em {melhor_piso}."
        bullet_idade = f"Posicionamento: Atualmente no {percentil_str} mundial entre os nascidos em {int(ano_nasc) if pd.notna(ano_nasc) else 'N/A'}."
        bullet_piso = f"Perfil Competitivo: O diferencial entre pisos indica um {tag_superficie.lower()}. A sua força no {melhor_piso} é o principal trunfo." if melhor_piso != "N/A" else "Perfil Competitivo: Histórico insuficiente para análise de superfícies."
        bullet_forma = f"Momento Recente (6 Meses): Registra {vitorias_6m}V - {derrotas_6m}D, resultando num Win Rate de {round(win_rate, 1)}%."

        return {
            "id": player_id, "nome": nome, "linha_meta": linha_meta,
            "idade": idade_aprox,
            "ano_nasc": int(ano_nasc) if pd.notna(ano_nasc) else "Desconhecido",
            "rank_itf": rank_itf,
            
            "headline": headline, "bullet_idade": bullet_idade, "bullet_piso": bullet_piso, "bullet_forma": bullet_forma,
            
            "elo_global_atual": round(elo_atual), "ranking_global": rank_global_elo, "diff_global": str_diff_global,
            
            "jogou_clay": jogou_clay, "elo_saibro": round(elo_saibro), "rank_clay": rank_clay, "med_clay": round(med_clay_idade), "diff_clay": str_diff_clay,
            "jogou_hard": jogou_hard, "elo_hard": round(elo_hard), "rank_hard": rank_hard, "med_hard": round(med_hard_idade), "diff_hard": str_diff_hard,
            "jogou_grass": jogou_grass, "elo_grass": round(elo_grass), "rank_grass": rank_grass, "med_grass": round(med_grass_idade), "diff_grass": str_diff_grass,
            
            "tag_superficie": tag_superficie, "melhor_piso": melhor_piso,
            
            "vitorias_6m": vitorias_6m, "derrotas_6m": derrotas_6m, "win_rate": round(win_rate, 1),
            
            "percentil_idade": percentil_str, "ranking_idade": f"{rank_na_idade}",
            "gaussiana_media_idade": int(round(media_idade)), "gaussiana_std_idade": int(round(std_idade)),
            "historico_completo": historico[['Tourney_Date', 'Surface', 'Meu_Elo', 'Meu_Elo_Surface', 'Resultado']]
        }

    def buscar_adversarios_dinamicos(self, player_id, dados_scout):
        adversarios = []
        ano_nasc = dados_scout.get('ano_nasc')
        elo_global = dados_scout['elo_global_atual']
        melhor_piso = dados_scout.get('melhor_piso', 'Saibro')
        rank_itf = dados_scout.get('rank_itf')
        nacionalidade = dados_scout.get('nacionalidade', 'BRA') # Fallback para garantir a regra

        # Tratar o rank para a lógica condicional
        rank_val = rank_itf if isinstance(rank_itf, int) else 9999
        
        # Filtra a si próprio
        pool = self.elos_atuais[(self.elos_atuais['Player_ID'].isin(self.lista_ativos)) & (self.elos_atuais['Player_ID'] != player_id)].copy() if self.lista_ativos else self.elos_atuais[self.elos_atuais['Player_ID'] != player_id].copy()
        if pool.empty: return []

        # Separar os compatriotas dos estrangeiros
        pool_nac = pool[pool['Nationality'] == nacionalidade]
        pool_gringo = pool[pool['Nationality'] != nacionalidade]
        
        ids_usados = set()
        
        def add_adv(row, piso, contexto):
            if str(row['Player_ID']) not in ids_usados:
                adversarios.append({"id": str(row['Player_ID']), "piso": piso, "contexto": contexto})
                ids_usados.add(str(row['Player_ID']))

        # ==========================================
        # MODO REGIONAL (Rank > 100) -> Foco Nacional
        # ==========================================
        if rank_val > 100 and len(pool_nac) >= 3:
            
            # 1. Alvo Nacional Acima (+ posições)
            acima = pool_nac[pool_nac['Elo'] > elo_global].sort_values('Elo', ascending=True)
            if not acima.empty:
                add_adv(acima.iloc[0], melhor_piso, f"Alvo {nacionalidade} (+ Posições)")
            
            # 2. Líder da Geração Nacional (Corrige quem é o #1)
            idade_nac = pool_nac[pool_nac['Birth_Year'] == ano_nasc].sort_values('Elo', ascending=False)
            for _, row in idade_nac.iterrows():
                if str(row['Player_ID']) not in ids_usados:
                    label = f"#1 da Geração {ano_nasc} ({nacionalidade})" if elo_global < row['Elo'] else f"#2 da Geração {ano_nasc} ({nacionalidade})"
                    add_adv(row, melhor_piso, label)
                    break
                    
            # 3. Rival Nacional Próximo
            proximo = pool_nac.iloc[(pool_nac['Elo'] - elo_global).abs().argsort()]
            for _, row in proximo.iterrows():
                if str(row['Player_ID']) not in ids_usados:
                    add_adv(row, melhor_piso, f"Rival Próximo ({nacionalidade})")
                    break

        # ==========================================
        # MODO ELITE (Rank <= 100) -> Ex: Guto Miguel
        # ==========================================
        else:
            
            # 1. Referência Nacional (Acima dele, ou o #2 do país se ele for o líder isolado)
            acima_nac = pool_nac[pool_nac['Elo'] > elo_global].sort_values('Elo', ascending=True)
            if not acima_nac.empty:
                add_adv(acima_nac.iloc[0], melhor_piso, f"Referência {nacionalidade} Acima")
            elif not pool_nac.empty:
                abaixo_nac = pool_nac.sort_values('Elo', ascending=False)
                add_adv(abaixo_nac.iloc[0], melhor_piso, f"#2 do Ranking {nacionalidade}")
                
            # 2. Líder da Geração Global (Corrige quem é o #1)
            idade_global = pool[pool['Birth_Year'] == ano_nasc].sort_values('Elo', ascending=False)
            for _, row in idade_global.iterrows():
                if str(row['Player_ID']) not in ids_usados:
                    label = f"#1 da Geração {ano_nasc} (Global)" if elo_global < row['Elo'] else f"#2 da Geração {ano_nasc} (Global)"
                    add_adv(row, "Piso Duro", label)
                    break
                    
            # 3. O "Boss" Estrangeiro (Gringo consideravelmente mais forte para desafio real)
            boss = pool_gringo[pool_gringo['Elo'] > elo_global + 80].sort_values('Elo', ascending=True)
            if not boss.empty:
                add_adv(boss.iloc[0], melhor_piso, "Desafio Internacional (Top Tier)")
            elif not pool_gringo.empty:
                # Se não há ninguém 80 pontos acima, bate de frente com o #1 do mundo absoluto
                add_adv(pool_gringo.sort_values('Elo', ascending=False).iloc[0], melhor_piso, "Desafio Internacional (Elite)")
                
        # Segurança: Se a base local for muito pequena, preenche os buracos com estrangeiros
        if len(adversarios) < 3:
            resto = pool.sort_values('Elo', ascending=False)
            for _, row in resto.iterrows():
                if str(row['Player_ID']) not in ids_usados:
                    add_adv(row, melhor_piso, "Benchmark de Rede")
                    if len(adversarios) == 3: break

        return adversarios
    
    def simular_confronto_ia(self, id_a, id_b, superficie='Saibro'):
        r_a, r_b = self.gerar_raio_x_jogador(id_a), self.gerar_raio_x_jogador(id_b)
        if "erro" in r_a or "erro" in r_b: return {"erro": "ID nao encontrado."}
        
        df_sim = pd.DataFrame({
            'elo_diff': [r_a['elo_global_atual'] - r_b['elo_global_atual']],
            'surface_elo_diff': [r_a.get({'Saibro':'elo_saibro', 'Piso Duro':'elo_hard', 'Grama':'elo_grass'}.get(superficie), 1500) - r_b.get({'Saibro':'elo_saibro', 'Piso Duro':'elo_hard', 'Grama':'elo_grass'}.get(superficie), 1500)],
            'age_diff': [(r_a['idade'] if r_a['idade'] != "N/A" else 18) - (r_b['idade'] if r_b['idade'] != "N/A" else 18)]
        })
        caminho_modelo = os.path.join(self.pasta_dados, f"xgb_model_{self.chave}.json")
        if not os.path.exists(caminho_modelo): return {"erro": "Modelo nao encontrado."}
        
        modelo_ia = xgb.XGBClassifier()
        modelo_ia.load_model(caminho_modelo)
        prob_a = modelo_ia.predict_proba(df_sim)[0][1]
        
        return {"jogador_a": r_a['nome'], "jogador_b": r_b['nome'], "superficie": superficie, "probabilidade_vitoria_a": round(prob_a * 100, 2)}
    
    def gerar_matriz_confrontos(self, player_id):
        """Gera probabilidades contra todos os jogadores ativos do circuito em lote."""
        raio_a = self.gerar_raio_x_jogador(player_id)
        if "erro" in raio_a: return None
        
        print(f"Calculando Matriz Global para {raio_a['nome']}...")
        
        # 1. Isolar ativos e remover o próprio jogador
        if not self.lista_ativos: return None
        ativos = self.elos_atuais[(self.elos_atuais['Player_ID'].isin(self.lista_ativos)) & (self.elos_atuais['Player_ID'] != player_id)].copy()
        
        # 2. Puxar Rankings ITF oficiais
        ativos['Rank_ITF'] = ativos['Player_ID'].map(self.dict_ranks_itf)
        ativos = ativos.dropna(subset=['Rank_ITF']).copy()
        ativos['Rank_ITF'] = ativos['Rank_ITF'].astype(int)
        
        # 3. Puxar Elos de Superfície
        ativos = ativos.merge(self.elos_clay[['Player_ID', 'Elo']], on='Player_ID', how='left', suffixes=('', '_clay'))
        ativos = ativos.merge(self.elos_hard[['Player_ID', 'Elo']], on='Player_ID', how='left', suffixes=('', '_hard'))
        ativos = ativos.merge(self.elos_grass[['Player_ID', 'Elo']], on='Player_ID', how='left', suffixes=('', '_grass'))
        ativos.fillna({'Elo_clay': 1500, 'Elo_hard': 1500, 'Elo_grass': 1500, 'Birth_Year': datetime.now().year - 18}, inplace=True)
        
        # 4. Montar os vetores de simulação
        idade_a = raio_a['idade'] if raio_a['idade'] != "N/A" else 18
        ativos['age_diff'] = idade_a - (datetime.now().year - ativos['Birth_Year'].astype(float))
        ativos['elo_diff'] = raio_a['elo_global_atual'] - ativos['Elo']
        
        df_clay = pd.DataFrame({'elo_diff': ativos['elo_diff'], 'surface_elo_diff': raio_a.get('elo_saibro', 1500) - ativos['Elo_clay'], 'age_diff': ativos['age_diff']})
        df_hard = pd.DataFrame({'elo_diff': ativos['elo_diff'], 'surface_elo_diff': raio_a.get('elo_hard', 1500) - ativos['Elo_hard'], 'age_diff': ativos['age_diff']})
        df_grass = pd.DataFrame({'elo_diff': ativos['elo_diff'], 'surface_elo_diff': raio_a.get('elo_grass', 1500) - ativos['Elo_grass'], 'age_diff': ativos['age_diff']})
        
        # 5. Predição em Massa (XGBoost)
        caminho_modelo = os.path.join(self.pasta_dados, f"xgb_model_{self.chave}.json")
        modelo_ia = xgb.XGBClassifier()
        modelo_ia.load_model(caminho_modelo)
        
        # Calculando a probabilidade crua (sem arredondar ainda)
        ativos['prob_clay'] = modelo_ia.predict_proba(df_clay)[:, 1] * 100
        ativos['prob_hard'] = modelo_ia.predict_proba(df_hard)[:, 1] * 100
        ativos['prob_grass'] = modelo_ia.predict_proba(df_grass)[:, 1] * 100
        
        # 6. Ordenar por Ranking ITF e formatar saída cravando 2 casas decimais
        ativos = ativos.sort_values('Rank_ITF')
        
        matriz = []
        for _, row in ativos.iterrows():
            matriz.append({
                "nome": row['Name'], "nacionalidade": row['Nationality'], "rank_itf": row['Rank_ITF'],
                "prob_hard": f"{row['prob_hard']:.2f}",
                "prob_clay": f"{row['prob_clay']:.2f}",
                "prob_grass": f"{row['prob_grass']:.2f}"
            })
            
        return {"nome_jogador": raio_a['nome'], "matriz": matriz}