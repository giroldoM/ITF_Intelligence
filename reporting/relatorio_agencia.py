import os
import pathlib
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# IMPORTANTE: Importar os motores de inteligência que já processam o Elo
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
        
        print("A iniciar o Motor de Inteligência para consolidar os Ratings globais...")
        self.motor_m = MotorInteligencia(chave='M')
        self.motor_w = MotorInteligencia(chave='W')

    def preparar_dataframe(self, motor):
        # Vai buscar o dataframe com os Elos finais calculados pelo próprio motor
        df = motor.elos_atuais.copy()
        
        # Calcular a idade baseada no ano de nascimento
        ano_atual = datetime.now().year
        df['Idade'] = ano_atual - pd.to_numeric(df['Birth_Year'], errors='coerce')
        
        # Garantir que o Player_ID é uma string limpa para cruzamento
        df['PlayerID'] = df['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        return df

    def gerar_mapa_talentos(self, df_circuito, ids_agencia, nomes_agencia, caminho_salvar, cor_destaque):
        plt.figure(figsize=(10, 5))
        ax = plt.gca()
        
        # Fundo Paper 0
        ax.set_facecolor('#FFFFFF')
        
        idade_col = 'Idade'
        elo_col = 'Elo'
        id_col = 'PlayerID'
        
        # 1. Circuito Global (Line 300 - neutro e translúcido)
        plt.scatter(df_circuito[idade_col], df_circuito[elo_col], 
                    color='#CBD5E1', alpha=0.3, s=20, label='Circuito Global')
        
        # 2. Atletas da Agência (Cor de destaque injetada)
        df_agencia = df_circuito[df_circuito[id_col].isin(ids_agencia)].copy()
        plt.scatter(df_agencia[idade_col], df_agencia[elo_col], 
                    color=cor_destaque, edgecolor='#FFFFFF', linewidth=1, 
                    alpha=1.0, s=120, label='Atletas da Agência')
        
        # 3. Etiquetas (Ink 900)
        for _, row in df_agencia.iterrows():
            idx = ids_agencia.index(row[id_col])
            nome = nomes_agencia[idx]
            plt.annotate(
                nome, (row[idade_col], row[elo_col]),
                xytext=(8, 8), textcoords='offset points',
                fontsize=9, weight='bold', color='#0B1220',
                bbox=dict(boxstyle="square,pad=0.2", fc="#FFFFFF", ec="#CBD5E1", lw=1, alpha=0.9) # Box mais retangular/stealth
            )
            
        # 4. Acabamento Tufte/Few (Slate 600 para eixos, Grid 200 para linhas)
        plt.xlabel('Idade', weight='bold', color='#475569', fontsize=10)
        plt.ylabel('Rating ELO', weight='bold', color='#475569', fontsize=10)
        ax.tick_params(colors='#475569', labelsize=9)
        
        for spine in ax.spines.values(): 
            spine.set_color('#E2E8F0') # Grid 200
            
        plt.grid(True, linestyle='-', alpha=1.0, color='#E2E8F0') # Linhas sólidas suaves
        plt.tight_layout()
        plt.savefig(caminho_salvar, dpi=300, bbox_inches='tight')
        plt.close()
        
        lista_final = []
        for _, row in df_agencia.iterrows():
            idx = ids_agencia.index(row[id_col])
            lista_final.append({"nome": nomes_agencia[idx], "id": row[id_col], "elo": round(row[elo_col], 1)})
        return lista_final

    def compilar(self):
        print("--- A GERAR RELATÓRIO DA AGÊNCIA ---")
        
        # 1. Obter DataFrames preparados pelo Motor de Inteligência (com Elo e Idade calculados)
        df_m = self.preparar_dataframe(self.motor_m)
        df_w = self.preparar_dataframe(self.motor_w)
        
        # 2. Caminhos para as imagens
        img_m = os.path.join(self.pasta_destino, "mapa_m.png")
        img_w = os.path.join(self.pasta_destino, "mapa_w.png")
        
        # 3. Gerar Gráficos e Obter Dados Atualizados (AQUI ENTRAM AS NOVAS CORES)
        ids_m = [str(a['id']) for a in ATLETAS_MASCULINOS]
        nomes_m = [a['nome'] for a in ATLETAS_MASCULINOS]
        # Divisão Masculina usando o Primary Blue
        dados_tabela_m = self.gerar_mapa_talentos(df_m, ids_m, nomes_m, img_m, '#1D4ED8')
        
        ids_w = [str(a['id']) for a in ATLETAS_FEMININOS]
        nomes_w = [a['nome'] for a in ATLETAS_FEMININOS]
        # Divisão Feminina usando o Teal Signal
        dados_tabela_w = self.gerar_mapa_talentos(df_w, ids_w, nomes_w, img_w, '#0F766E')

        # [Dentro do def compilar(self), adicione logo abaixo da geração dos dados_tabela_w...]
        
        # Caminhos para os novos gráficos
        img_sup_m = os.path.join(self.pasta_destino, "superficies_m.png")
        img_sup_w = os.path.join(self.pasta_destino, "superficies_w.png")
        
        # Gerar os gráficos de superfície comparativos
        self.gerar_comparativo_superficies(self.motor_m, ids_m, img_sup_m)
        self.gerar_comparativo_superficies(self.motor_w, ids_w, img_sup_w)
        
        # No dicionário "contexto", adicione estas duas novas variáveis:
        contexto = {
            "data_geracao": datetime.now().strftime('%d/%m/%Y'),
            "grafico_dispersao_m": f"file://{img_m}",
            "grafico_dispersao_w": f"file://{img_w}",
            "grafico_superficies_m": f"file://{img_sup_m}", # NOVO
            "grafico_superficies_w": f"file://{img_sup_w}", # NOVO
            "atletas_m": sorted(dados_tabela_m, key=lambda x: x['elo'], reverse=True),
            "atletas_w": sorted(dados_tabela_w, key=lambda x: x['elo'], reverse=True)
        }
        
        # 4. Renderizar PDF
        # 4. Renderizar PDF
        contexto = {
            "data_geracao": datetime.now().strftime('%d/%m/%Y'),
            # O pathlib transforma o caminho do Windows num formato que o WeasyPrint lê perfeitamente
            "grafico_dispersao_m": pathlib.Path(img_m).as_uri(),
            "grafico_dispersao_w": pathlib.Path(img_w).as_uri(),
            "grafico_superficies_m": pathlib.Path(img_sup_m).as_uri(),
            "grafico_superficies_w": pathlib.Path(img_sup_w).as_uri(),
            "atletas_m": sorted(dados_tabela_m, key=lambda x: x['elo'], reverse=True),
            "atletas_w": sorted(dados_tabela_w, key=lambda x: x['elo'], reverse=True)
        }
        
        template = self.env.get_template('relatorio_agencia.html')
        html_renderizado = template.render(contexto)
        
        caminho_pdf = os.path.join(self.pasta_destino, "Relatorio_Consolidado_Agencia.pdf")
        HTML(string=html_renderizado, base_url=self.diretorio_atual).write_pdf(caminho_pdf)
        
        print(f"Sucesso! PDF gerado em: {caminho_pdf}")

    def gerar_comparativo_superficies(self, motor, ids_agencia, caminho_salvar):
        """Gera um gráfico comparando a média de Elo da Agência vs Circuito por piso."""
        import numpy as np
        
        # 1. Extrair os dados dos motores
        df_clay = motor.elos_clay.copy()
        df_hard = motor.elos_hard.copy()
        df_grass = motor.elos_grass.copy()
        
        # Garantir IDs limpos
        df_clay['PlayerID'] = df_clay['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        df_hard['PlayerID'] = df_hard['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        df_grass['PlayerID'] = df_grass['Player_ID'].astype(str).str.replace('.0', '', regex=False)
        
        # 2. Calcular Médias Globais
        media_glb = [
            df_clay['Elo'].mean(),
            df_hard['Elo'].mean(),
            df_grass['Elo'].mean()
        ]
        
        # 3. Calcular Médias da Agência
        media_ag = [
            df_clay[df_clay['PlayerID'].isin(ids_agencia)]['Elo'].mean(),
            df_hard[df_hard['PlayerID'].isin(ids_agencia)]['Elo'].mean(),
            df_grass[df_grass['PlayerID'].isin(ids_agencia)]['Elo'].mean()
        ]
        
        # Lidar com casos onde a agência não tem jogos num piso (ex: Grama)
        media_ag = [m if not np.isnan(m) else 1500 for m in media_ag]

        # 4. Configuração do Gráfico
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_facecolor('#FFFFFF')
        
        x = np.arange(3)
        largura = 0.35
        
        cores_agencia = ['#A65A3A', '#5B6E91', '#5C7F62'] # Clay, Hard, Grass
        cor_global = '#CBD5E1' # Neutro Line 300
        
        # Desenhar as barras
        barras_glb = ax.bar(x - largura/2, media_glb, largura, label='Média Global', color=cor_global)
        barras_ag = ax.bar(x + largura/2, media_ag, largura, label='Média Agência', color=cores_agencia)
        
        # Adicionar os valores no topo das barras (Tipografia tabular/limpa)
        for barra in barras_glb:
            altura = barra.get_height()
            ax.annotate(f'{int(altura)}',
                        xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, color='#94A3B8', weight='bold')
                        
        for barra in barras_ag:
            altura = barra.get_height()
            ax.annotate(f'{int(altura)}',
                        xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, color='#0B1220', weight='bold')

        # Estilização B2B / Few
        ax.set_xticks(x)
        ax.set_xticklabels(['Saibro', 'Piso Duro', 'Grama'], fontsize=11, weight='bold', color='#475569')
        ax.set_ylim(1300, max(max(media_glb), max(media_ag)) + 150) # Começar num baseline lógico de Elo
        ax.set_ylabel('Rating ELO Médio', weight='bold', color='#475569', fontsize=10)
        
        ax.tick_params(colors='#475569', labelsize=9)
        for spine in ax.spines.values(): 
            spine.set_color('#E2E8F0')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
            
        plt.grid(axis='y', linestyle='-', alpha=1.0, color='#E2E8F0')
        
        # Legenda minimalista
        import matplotlib.patches as mpatches
        leg_glb = mpatches.Patch(color=cor_global, label='Circuito Global')
        leg_ag = mpatches.Patch(color='#1E293B', label='Atletas da Agência')
        ax.legend(handles=[leg_glb, leg_ag], frameon=False, fontsize=10, loc='upper left')
        
        plt.tight_layout()
        plt.savefig(caminho_salvar, dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    app = RelatorioAgencia()
    app.compilar()