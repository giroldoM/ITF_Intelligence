import matplotlib.pyplot as plt

def plotar_mapa_talentos_agencia(df_circuito, df_agencia, caminho_salvar):
    """
    df_circuito: DataFrame com colunas ['Idade', 'Elo'] de todos os top 4000
    df_agencia: DataFrame com colunas ['Idade', 'Elo', 'Nome'] dos atletas da agência
    """
    plt.figure(figsize=(11, 7))
    ax = plt.gca()
    
    # Fundo branco e limpo corporativo
    ax.set_facecolor('#ffffff')
    
    # 1. Plotar o resto do mundo (cinza claro, pequeno)
    plt.scatter(df_circuito['Idade'], df_circuito['Elo'], 
                color='#cbd5e1', alpha=0.4, s=30, label='Circuito Mundial (ITF)')
    
    # 2. Plotar os atletas da Agência (azul escuro premium, maior)
    plt.scatter(df_agencia['Idade'], df_agencia['Elo'], 
                color='#0284c7', edgecolor='#0c4a6e', linewidth=1.5, 
                alpha=1.0, s=150, label='Atletas da Agência')
    
    # 3. Colocar o nome de cada atleta da agência do lado do seu ponto
    for i, row in df_agencia.iterrows():
        plt.annotate(
            row['Nome'], 
            (row['Idade'], row['Elo']),
            xytext=(8, 8), textcoords='offset points',
            fontsize=10, weight='bold', color='#0f172a',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cbd5e1", lw=1, alpha=0.8)
        )
        
    # 4. Estilização do Gráfico
    plt.title('Mapa de Talentos: Idade vs. Força (Rating ELO)', 
              fontsize=16, weight='bold', color='#0f172a', pad=20)
    plt.xlabel('Idade do Atleta', fontsize=12, weight='bold', color='#475569')
    plt.ylabel('Rating Global ELO', fontsize=12, weight='bold', color='#475569')
    
    ax.tick_params(colors='#475569', labelsize=11)
    for spine in ax.spines.values():
        spine.set_color('#e2e8f0')
        
    plt.grid(True, linestyle='--', alpha=0.5, color='#94a3b8')
    plt.legend(frameon=True, facecolor='white', edgecolor='#cbd5e1', fontsize=11, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(caminho_salvar, dpi=300, bbox_inches='tight')
    plt.close()