import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.dates as mdates
from math import pi
import os

class EstudioGrafico:
    def __init__(self, output_dir='outputs'):
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.output_path = os.path.join(diretorio_atual, output_dir)
        
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        # PALETA DE CORES B2B (ITF Intelligence)
        self.colors = {
            'text_main': '#0B1220',      # Ink 900
            'text_sec': '#475569',       # Slate 600
            'axis_light': '#CBD5E1',     # Line 300
            'grid_light': '#E2E8F0',     # Grid 200
            'brand_primary': '#1D4ED8',  # Primary Blue
            'brand_bg_shade': '#1D4ED8', # Primary Blue (para usar com alpha/transparência)
            'positive': '#15803D',       # Positive Green
            'negative': '#A63A50',       # Negative Red
            'clay': '#A65A3A',
            'hard': '#5B6E91',
            'grass': '#5C7F62',
            'gray_curve': '#94A3B8'      # Slate 400
        }
        
        self._configurar_tema_minimalista()

    def _configurar_tema_minimalista(self):
        # Remove todo o "chart junk"
        sns.set_theme(style="white", font="sans-serif")
        plt.rcParams.update({
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.spines.left': False,
            'axes.edgecolor': self.colors['axis_light'],
            'text.color': self.colors['text_main'],
            'xtick.color': self.colors['text_sec'],
            'ytick.color': self.colors['text_sec'],
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.titleweight': 'bold',
            'axes.titlecolor': self.colors['text_main'],
            'figure.facecolor': '#FFFFFF',
            'axes.facecolor': '#FFFFFF',
        })

    def gerar_sparkline_evolucao(self, df_historico, player_id):
        """Sparkline temporal focado na tendência, sem ruído."""
        if df_historico.empty: return None

        df_plot = df_historico.tail(30).copy() # Foco no momento recente
        
        fig, ax = plt.subplots(figsize=(6, 2)) # Formato achatado e conciso
        
        # Determinar cor pela tendência (positivo ou negativo)
        elo_inicial = df_plot.iloc[0]['Meu_Elo']
        elo_final = df_plot.iloc[-1]['Meu_Elo']
        cor_linha = self.colors['positive'] if elo_final >= elo_inicial else self.colors['negative']

        ax.plot(df_plot['Tourney_Date'], df_plot['Meu_Elo'], color=cor_linha, linewidth=2.5)
        
        # Marcador apenas no último ponto para destacar a posição atual
        ax.plot(df_plot['Tourney_Date'].iloc[-1], elo_final, marker='o', color=cor_linha, markersize=6)

        # Eixos minimalistas
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.yaxis.set_visible(False) # Esconde os números do eixo Y para focar na forma
        ax.spines['bottom'].set_linewidth(1)
        
        plt.tight_layout()
        caminho_arquivo = os.path.join(self.output_path, f"sparkline_{player_id}.png")
        plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        return caminho_arquivo

    def gerar_gaussiana(self, media, std, elo_atleta, player_id):
        """Curva de distribuição normal para o Age-Adjusted Rating."""
        fig, ax = plt.subplots(figsize=(6, 2.5))

        # Eixo X matemático: da média - 4 std até média + 4 std
        x = np.linspace(media - 4*std, media + 4*std, 500)
        y = stats.norm.pdf(x, media, std)

        # Desenhar a curva cinza
        ax.plot(x, y, color=self.colors['gray_curve'], linewidth=1.5)

        # Preenchimento (Shading) apenas na cauda onde o atleta está
        if elo_atleta >= media:
            x_fill = np.linspace(elo_atleta, media + 4*std, 100)
        else:
            x_fill = np.linspace(media - 4*std, elo_atleta, 100)
        
        y_fill = stats.norm.pdf(x_fill, media, std)
        ax.fill_between(x_fill, y_fill, color=self.colors['brand_bg_shade'], alpha=0.15)

        # Linha da Média (Neutro)
        ax.axvline(media, color=self.colors['axis_light'], linestyle='--', linewidth=1)
        
        # Linha do Atleta (Destaque)
        altura_atleta = stats.norm.pdf(elo_atleta, media, std)
        ax.vlines(x=elo_atleta, ymin=0, ymax=altura_atleta, color=self.colors['brand_primary'], linewidth=2)
        ax.plot(elo_atleta, altura_atleta, marker='o', color=self.colors['brand_primary'], markersize=6) # Ponto no topo

        # Limpeza total dos eixos
        ax.yaxis.set_visible(False)
        ax.spines['bottom'].set_color(self.colors['axis_light'])
        
        # Deixar apenas 2 números no eixo X: A média e o Atleta
        ax.set_xticks([media, elo_atleta])
        ax.set_xticklabels([f"Média: {int(media)}", f"Atleta: {int(elo_atleta)}"], fontweight='bold')

        plt.tight_layout()
        caminho_arquivo = os.path.join(self.output_path, f"gaussiana_{player_id}.png")
        plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        return caminho_arquivo

    def gerar_radar_superficies(self, elo_saibro, elo_hard, elo_grass, player_id):
        """Radar chart minimalista estrito, normalizado internamente."""
        fig, ax = plt.subplots(figsize=(3, 3), subplot_kw=dict(polar=True))
        
        categorias = ['Saibro', 'Rápido', 'Grama']
        elos = [elo_saibro, elo_hard, elo_grass]
        N = len(categorias)
        
        # Ângulos matemáticos
        angles = [n / float(N) * 2 * pi for n in range(N)]
        angles += angles[:1]
        elos += elos[:1] # Fechar o polígono

        # Remover bordas escuras e configurar grids finos
        ax.spines['polar'].set_visible(False)
        ax.grid(color=self.colors['grid_light'], linewidth=0.5)
        
        # Rótulos (Omitindo os números e deixando apenas as superfícies)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categorias, color=self.colors['text_sec'], size=9, weight='bold')
        
        # Posição e cores dos rótulos (ajuste fino)
        for label, color in zip(ax.get_xticklabels(), [self.colors['clay'], self.colors['hard'], self.colors['grass']]):
            label.set_color(color)

        # Grid rings limitados a 3 aneis (como pedido pelo consultor)
        min_elo = min(elos[:-1]) - 100
        max_elo = max(elos[:-1]) + 50
        ax.set_ylim(min_elo, max_elo)
        ax.set_yticks(np.linspace(min_elo, max_elo, 3))
        ax.set_yticklabels([]) # Sem radial tick labels!

        # Desenhar o polígono principal
        ax.plot(angles, elos, color=self.colors['brand_primary'], linewidth=2)
        ax.fill(angles, elos, color=self.colors['brand_bg_shade'], alpha=0.08) # Fill de 8% maximo

        plt.tight_layout()
        caminho_arquivo = os.path.join(self.output_path, f"radar_{player_id}.png")
        plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        return caminho_arquivo

# --- TESTE INTEGRADO ---
if __name__ == "__main__":
    from motor_inteligencia import MotorInteligencia
    
    print("1. Extraindo dados da inteligência para os gráficos...")
    motor = MotorInteligencia(chave='W')
    id_alvo = "800655335" # Exemplo: Victoria Barros
    dados = motor.gerar_raio_x_jogador(id_alvo)
    
    print("2. Desenhando as visualizações matemáticas B2B...")
    estudio = EstudioGrafico()
    
    caminho_spark = estudio.gerar_sparkline_evolucao(dados['historico_completo'], id_alvo)
    caminho_gauss = estudio.gerar_gaussiana(dados['gaussiana_media_idade'], dados['gaussiana_std_idade'], dados['elo_global_atual'], id_alvo)
    caminho_radar = estudio.gerar_radar_superficies(dados['elo_saibro'], dados['elo_hard'], dados['elo_grass'], id_alvo)
    
    print(f"\n--- SUCESSO! ---")
    print(f"Abra a pasta 'outputs' e veja a qualidade das 3 novas imagens geradas.")