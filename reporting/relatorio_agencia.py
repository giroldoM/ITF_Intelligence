import os
import pathlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from motor_inteligencia import MotorInteligencia

# ==========================================
# DADOS DA AGÊNCIA
# ==========================================
ATLETAS_MASCULINOS = [
    {"nome": "Henrique Queiroz", "id": "800684304"},
    {"nome": "Livas Damazio", "id": "800716347"},
    {"nome": "Luis Guto Miguel", "id": "800680259"},
    {"nome": "Lucas Moscatto", "id": "800695229"},
    {"nome": "Pedro Dietrich", "id": "800642706"}
]

ATLETAS_FEMININOS = [
    {"nome": "Nauhany Silva", "id": "800695060"},
    {"nome": "Pietra Rivoli", "id": "800655734"}
]

class RelatorioAgencia:
    def __init__(self):
        self.diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.pasta_destino = os.path.join(self.diretorio_atual, 'outputs', datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(self.pasta_destino, exist_ok=True)
        
        self.env = Environment(loader=FileSystemLoader(os.path.join(self.diretorio_atual, 'templates')))
        
        print("A iniciar os Motores de Inteligência para consolidar os Ratings globais...")
        self.motor_m = MotorInteligencia(chave='M')
        self.motor_w = MotorInteligencia(chave='W')

    def preparar_dataframe(self, motor):
        df = motor.elos_atuais.copy()
        ano_atual = datetime.now().year
        df['Idade'] = ano_atual - pd.to_numeric(df['Birth_Year'], errors='coerce')
        df['PlayerID'] = df['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        return df

    def gerar_mapa_talentos(self, df_circuito, ids_agencia, nomes_agencia, caminho_salvar, cor_destaque):
        plt.figure(figsize=(10, 5))
        ax = plt.gca()
        ax.set_facecolor('#FFFFFF')
        
        idade_col, elo_col, id_col = 'Idade', 'Elo', 'PlayerID'
        
        plt.scatter(df_circuito[idade_col], df_circuito[elo_col], 
                    color='#CBD5E1', alpha=0.3, s=20, label='Circuito Global')
        
        df_agencia = df_circuito[df_circuito[id_col].isin(ids_agencia)].copy()
        plt.scatter(df_agencia[idade_col], df_agencia[elo_col], 
                    color=cor_destaque, edgecolor='#FFFFFF', linewidth=1, 
                    alpha=1.0, s=120, label='Atletas da Agência')
        
        for _, row in df_agencia.iterrows():
            idx = ids_agencia.index(row[id_col])
            nome = nomes_agencia[idx]
            plt.annotate(
                nome, (row[idade_col], row[elo_col]),
                xytext=(8, 8), textcoords='offset points',
                fontsize=9, weight='bold', color='#0B1220',
                bbox=dict(boxstyle="square,pad=0.2", fc="#FFFFFF", ec="#CBD5E1", lw=1, alpha=0.9)
            )
            
        plt.xlabel('Idade', weight='bold', color='#475569', fontsize=10)
        plt.ylabel('Rating ELO', weight='bold', color='#475569', fontsize=10)
        ax.tick_params(colors='#475569', labelsize=9)
        
        for spine in ax.spines.values(): spine.set_color('#E2E8F0')
        plt.grid(True, linestyle='-', alpha=1.0, color='#E2E8F0')
        plt.tight_layout()
        plt.savefig(caminho_salvar, dpi=300, bbox_inches='tight')
        plt.close()
        
        lista_final = []
        for _, row in df_agencia.iterrows():
            idx = ids_agencia.index(row[id_col])
            lista_final.append({"nome": nomes_agencia[idx], "id": row[id_col], "elo": round(row[elo_col], 1)})
        return lista_final

    def gerar_comparativo_superficies(self, motor, ids_agencia, caminho_salvar):
        df_clay, df_hard, df_grass = motor.elos_clay.copy(), motor.elos_hard.copy(), motor.elos_grass.copy()
        
        for df in [df_clay, df_hard, df_grass]:
            df['PlayerID'] = df['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        
        media_glb = [df_clay['Elo'].mean(), df_hard['Elo'].mean(), df_grass['Elo'].mean()]
        
        media_ag = [
            df_clay[df_clay['PlayerID'].isin(ids_agencia)]['Elo'].mean(),
            df_hard[df_hard['PlayerID'].isin(ids_agencia)]['Elo'].mean(),
            df_grass[df_grass['PlayerID'].isin(ids_agencia)]['Elo'].mean()
        ]
        media_ag = [m if not np.isnan(m) else 1500 for m in media_ag]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_facecolor('#FFFFFF')
        
        x = np.arange(3)
        largura = 0.35
        
        barras_glb = ax.bar(x - largura/2, media_glb, largura, label='Média Global', color='#CBD5E1')
        barras_ag = ax.bar(x + largura/2, media_ag, largura, label='Média Agência', color=['#A65A3A', '#5B6E91', '#5C7F62'])
        
        for barra in barras_glb:
            altura = barra.get_height()
            ax.annotate(f'{int(altura)}', xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, color='#94A3B8', weight='bold')
                        
        for barra in barras_ag:
            altura = barra.get_height()
            ax.annotate(f'{int(altura)}', xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, color='#0B1220', weight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(['Saibro', 'Piso Duro', 'Grama'], fontsize=11, weight='bold', color='#475569')
        ax.set_ylim(1300, max(max(media_glb), max(media_ag)) + 150)
        ax.set_ylabel('Rating ELO Médio', weight='bold', color='#475569', fontsize=10)
        
        ax.tick_params(colors='#475569', labelsize=9)
        for spine in ax.spines.values(): spine.set_color('#E2E8F0')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.grid(axis='y', linestyle='-', alpha=1.0, color='#E2E8F0')
        
        import matplotlib.patches as mpatches
        ax.legend(handles=[mpatches.Patch(color='#CBD5E1', label='Circuito Global'), mpatches.Patch(color='#1E293B', label='Atletas da Agência')], 
                  frameon=False, fontsize=10, loc='upper left')
        
        plt.tight_layout()
        plt.savefig(caminho_salvar, dpi=300, bbox_inches='tight')
        plt.close()

    def gerar_macro_agencia_vs_resto(self, motor, ids_agencia, caminho_salvar, cor_destaque):
        df_matches = motor.df_matches.copy()
        if not df_matches.empty:
            data_corte = df_matches['Tourney_Date'].max() - pd.Timedelta(days=365)
            df_12m = df_matches[df_matches['Tourney_Date'] >= data_corte].copy()
        else:
            df_12m = df_matches

        total_jogos_glb = len(df_12m)
        win_rate_glb = 50.0
        upsets_glb = len(df_12m[df_12m['Loser_Global_Elo'] > (df_12m['Winner_Global_Elo'] + 50)])
        tx_upset_glb = (upsets_glb / total_jogos_glb) * 100 if total_jogos_glb > 0 else 0
        esperados_glb = len(df_12m[df_12m['Winner_Global_Elo'] > df_12m['Loser_Global_Elo']])
        tx_esperados_glb = (esperados_glb / total_jogos_glb) * 100 if total_jogos_glb > 0 else 0

        vitorias_ag = df_12m[df_12m['winner_id'].isin(ids_agencia)]
        derrotas_ag = df_12m[df_12m['loser_id'].isin(ids_agencia)]
        total_jogos_ag = len(vitorias_ag) + len(derrotas_ag)

        win_rate_ag = (len(vitorias_ag) / total_jogos_ag) * 100 if total_jogos_ag > 0 else 0
        upsets_ag = len(vitorias_ag[vitorias_ag['Loser_Global_Elo'] > (vitorias_ag['Winner_Global_Elo'] + 50)])
        tx_upset_ag = (upsets_ag / total_jogos_ag) * 100 if total_jogos_ag > 0 else 0
        esperados_ag = len(vitorias_ag[vitorias_ag['Winner_Global_Elo'] > vitorias_ag['Loser_Global_Elo']])
        tx_esperados_ag = (esperados_ag / total_jogos_ag) * 100 if total_jogos_ag > 0 else 0

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_facecolor('#FFFFFF')

        categorias = ['Taxa de Vitória\n(Win Rate Geral)', 'Taxa de Upset\n(Zebra/Superação)', 'Consistência\n(Aviso Confirmado)']
        x = np.arange(len(categorias))
        largura = 0.35

        barras_glb = ax.bar(x - largura/2, [win_rate_glb, tx_upset_glb, tx_esperados_glb], largura, label='Circuito Global', color='#CBD5E1')
        barras_ag = ax.bar(x + largura/2, [win_rate_ag, tx_upset_ag, tx_esperados_ag], largura, label='Portfólio da Agência', color=cor_destaque)

        for barra in barras_glb:
            h = barra.get_height()
            ax.annotate(f'{h:.1f}%', xy=(barra.get_x() + barra.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, color='#94A3B8', weight='bold')
        for barra in barras_ag:
            h = barra.get_height()
            ax.annotate(f'{h:.1f}%', xy=(barra.get_x() + barra.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, color='#0B1220', weight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(categorias, fontsize=11, weight='bold', color='#475569')
        ax.set_ylim(0, max(max([win_rate_glb, tx_upset_glb, tx_esperados_glb]), max([win_rate_ag, tx_upset_ag, tx_esperados_ag])) + 15)
        ax.set_ylabel('Percentagem (%)', weight='bold', color='#475569', fontsize=10)

        ax.tick_params(colors='#475569', labelsize=9)
        for spine in ax.spines.values(): spine.set_color('#E2E8F0')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.grid(axis='y', linestyle='-', alpha=1.0, color='#E2E8F0')

        import matplotlib.patches as mpatches
        ax.legend(handles=[mpatches.Patch(color='#CBD5E1', label='Circuito Global (Resto)'), mpatches.Patch(color=cor_destaque, label='Agência')], frameon=False, fontsize=10, loc='upper left')

        plt.tight_layout()
        plt.savefig(caminho_salvar, dpi=300, bbox_inches='tight')
        plt.close()

    def calcular_insights_agencia(self, motor, ids_agencia, nomes_agencia):
        df_matches = motor.df_matches.copy()
        
        if not df_matches.empty:
            data_corte = df_matches['Tourney_Date'].max() - pd.Timedelta(days=365)
            df_matches_12m = df_matches[df_matches['Tourney_Date'] >= data_corte]
        else:
            df_matches_12m = df_matches
            
        insights = []
        for i, pid in enumerate(ids_agencia):
            vitorias = df_matches_12m[df_matches_12m['winner_id'] == str(pid)].copy()
            derrotas = df_matches_12m[df_matches_12m['loser_id'] == str(pid)].copy()
            
            total_jogos = len(vitorias) + len(derrotas)
            
            # Se não tiver jogos no último ano
            if total_jogos == 0:
                insights.append({
                    "nome": nomes_agencia[i], 
                    "carga": 0, 
                    "alerta_carga": "text-warning", 
                    "upsets": 0
                })
                continue
                
            # Calcular o Índice "Giant Killer" (Vitórias sobre adversários com +50 de Elo)
            upsets = len(vitorias[vitorias['Loser_Global_Elo'] > (vitorias['Winner_Global_Elo'] + 50)])
            
            # Alerta de Carga (Mais de 65 jogos acende o alerta vermelho)
            alerta_carga = "text-negative" if total_jogos > 65 else "text-positive" if total_jogos > 30 else ""

            insights.append({
                "nome": nomes_agencia[i],
                "carga": total_jogos,
                "alerta_carga": alerta_carga,
                "upsets": upsets
            })
            
        # Ordenar pelos atletas com mais vitórias épicas (Giant Killers)
        return sorted(insights, key=lambda x: x['upsets'], reverse=True)
            
        return sorted(insights, key=lambda x: x['upsets'], reverse=True)

    def compilar(self):
        print("--- A GERAR RELATÓRIO DA AGÊNCIA ---")
        
        df_m = self.preparar_dataframe(self.motor_m)
        df_w = self.preparar_dataframe(self.motor_w)
        
        img_m = os.path.join(self.pasta_destino, "mapa_m.png")
        img_w = os.path.join(self.pasta_destino, "mapa_w.png")
        
        ids_m = [str(a['id']) for a in ATLETAS_MASCULINOS]
        nomes_m = [a['nome'] for a in ATLETAS_MASCULINOS]
        dados_tabela_m = self.gerar_mapa_talentos(df_m, ids_m, nomes_m, img_m, '#1D4ED8')
        
        ids_w = [str(a['id']) for a in ATLETAS_FEMININOS]
        nomes_w = [a['nome'] for a in ATLETAS_FEMININOS]
        dados_tabela_w = self.gerar_mapa_talentos(df_w, ids_w, nomes_w, img_w, '#0F766E')

        img_sup_m = os.path.join(self.pasta_destino, "superficies_m.png")
        img_sup_w = os.path.join(self.pasta_destino, "superficies_w.png")
        self.gerar_comparativo_superficies(self.motor_m, ids_m, img_sup_m)
        self.gerar_comparativo_superficies(self.motor_w, ids_w, img_sup_w)
        
        img_macro_m = os.path.join(self.pasta_destino, "macro_m.png")
        img_macro_w = os.path.join(self.pasta_destino, "macro_w.png")
        self.gerar_macro_agencia_vs_resto(self.motor_m, ids_m, img_macro_m, '#1D4ED8') 
        self.gerar_macro_agencia_vs_resto(self.motor_w, ids_w, img_macro_w, '#0F766E') 

        insights_m = self.calcular_insights_agencia(self.motor_m, ids_m, nomes_m)
        insights_w = self.calcular_insights_agencia(self.motor_w, ids_w, nomes_w)

        contexto = {
            "data_geracao": datetime.now().strftime('%d/%m/%Y'),
            "grafico_dispersao_m": pathlib.Path(img_m).as_uri(),
            "grafico_dispersao_w": pathlib.Path(img_w).as_uri(),
            "grafico_superficies_m": pathlib.Path(img_sup_m).as_uri(),
            "grafico_superficies_w": pathlib.Path(img_sup_w).as_uri(),
            "grafico_macro_m": pathlib.Path(img_macro_m).as_uri(),
            "grafico_macro_w": pathlib.Path(img_macro_w).as_uri(),
            "atletas_m": sorted(dados_tabela_m, key=lambda x: x['elo'], reverse=True),
            "atletas_w": sorted(dados_tabela_w, key=lambda x: x['elo'], reverse=True),
            "insights_m": insights_m,
            "insights_w": insights_w
        }
        
        template = self.env.get_template('relatorio_agencia.html')
        html_renderizado = template.render(contexto)
        
        caminho_pdf = os.path.join(self.pasta_destino, "Relatorio_Consolidado_Agencia.pdf")
        HTML(string=html_renderizado, base_url=self.diretorio_atual).write_pdf(caminho_pdf)
        
        print(f"Sucesso! PDF gerado em: {caminho_pdf}")

if __name__ == "__main__":
    app = RelatorioAgencia()
    app.compilar()