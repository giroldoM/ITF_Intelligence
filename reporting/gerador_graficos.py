import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.dates as mdates

class EstudioGrafico:
    def __init__(self, output_dir='outputs'):
        """
        Inicializa o estúdio e garante que a pasta de outputs das imagens existe.
        """
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.output_path = os.path.join(diretorio_atual, output_dir)
        
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        self._configurar_tema_premium()

    def _configurar_tema_premium(self):
        """
        Aplica um estilo corporativo limpo ao Seaborn, removendo o 'chart junk'.
        """
        sns.set_theme(style="white", font="sans-serif")
        plt.rcParams.update({
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.spines.left': False,
            'axes.linewidth': 1.2,
            'axes.edgecolor': '#cccccc',
            'axes.labelcolor': '#555555',
            'xtick.color': '#777777',
            'ytick.color': '#777777',
            'text.color': '#333333',
            'font.size': 10,
            'axes.titlesize': 14,
            'axes.titleweight': 'bold'
        })

    def gerar_grafico_evolucao(self, df_historico, player_id):
        """
        Gera um gráfico de linha mostrando a evolução do Elo Global.
        """
        if df_historico.empty:
            return None

        # Limitar ao último ano e meio para não ficar achatado
        df_plot = df_historico.tail(50).copy()

        fig, ax = plt.subplots(figsize=(8, 4))
        
        # A linha de evolução
        sns.lineplot(
            data=df_plot, 
            x='Tourney_Date', 
            y='Meu_Elo', 
            ax=ax, 
            color='#0b2545', # Azul marinho profundo
            linewidth=3,
            marker='o',
            markersize=6,
            markerfacecolor='#eeb868', # Dourado nos pontos
            markeredgewidth=0
        )

        ax.set_title("Evolução do Rating (Últimos Jogos)")
        ax.set_xlabel("")
        ax.set_ylabel("Rating Global")
        
        # Formatar as datas no eixo X para ficarem legíveis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45, ha='right')
        
        # Linhas de grade horizontais muito suaves
        ax.yaxis.grid(True, linestyle='--', color='#eeeeee')
        
        plt.tight_layout()
        
        # Guardar a imagem
        caminho_arquivo = os.path.join(self.output_path, f"evolucao_{player_id}.png")
        plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight', transparent=False)
        plt.close()
        
        return caminho_arquivo

    def gerar_grafico_superficie(self, elo_saibro, elo_hard, player_id):
        """
        Gera um gráfico de barras comparando a força nos pisos.
        """
        fig, ax = plt.subplots(figsize=(5, 4))
        
        superficies = ['Saibro (Clay)', 'Rápido (Hard)']
        elos = [elo_saibro, elo_hard]
        cores = ['#e2725b', '#2a9d8f'] # Laranja terra batida e Verde/Azul cimento
        
        bars = ax.bar(superficies, elos, color=cores, width=0.5)
        
        ax.set_title("Força por Superfície")
        ax.set_ylim(min(elos) - 100, max(elos) + 50) # Dar um respiro no eixo Y
        
        # Colocar o número exato em cima de cada barra
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  
                        textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold', color='#333333')

        # Esconder eixo Y esquerdo inteiro para ficar mais limpo
        ax.get_yaxis().set_visible(False)
        ax.spines['bottom'].set_color('#cccccc')

        plt.tight_layout()
        
        caminho_arquivo = os.path.join(self.output_path, f"superficie_{player_id}.png")
        plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight', transparent=False)
        plt.close()
        
        return caminho_arquivo

# --- TESTE INTEGRADO ---
if __name__ == "__main__":
    from motor_inteligencia import MotorInteligencia
    
    print("1. Extraindo dados do Motor de Inteligência...")
    motor = MotorInteligencia(chave='W')
    
    # ID da Victoria Barros
    id_alvo = "800655335"
    dados_scout = motor.gerar_raio_x_jogador(id_alvo)
    
    print("\n2. Passando dados para o Estúdio Gráfico...")
    estudio = EstudioGrafico()
    
    # Gerando as duas imagens
    caminho_evolucao = estudio.gerar_grafico_evolucao(dados_scout['historico_completo'], id_alvo)
    caminho_superficie = estudio.gerar_grafico_superficie(dados_scout['elo_saibro'], dados_scout['elo_hard'], id_alvo)
    
    print(f"\n--- SUCESSO! ---")
    print(f"Gráfico de evolução guardado em: {caminho_evolucao}")
    print(f"Gráfico de superfície guardado em: {caminho_superficie}")