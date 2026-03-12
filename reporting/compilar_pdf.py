import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from motor_inteligencia import MotorInteligencia
from gerador_graficos import EstudioGrafico

class ConstrutorRelatorio:
    def __init__(self, chave='M'):
        self.motor = MotorInteligencia(chave=chave)
        self.estudio = EstudioGrafico()
        
        self.diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.pasta_templates = os.path.join(self.diretorio_atual, 'templates')
        self.pasta_outputs = os.path.join(self.diretorio_atual, 'outputs')
        
        self.env = Environment(loader=FileSystemLoader(self.pasta_templates))
    
    def gerar_relatorio_individual(self, player_id, benchmark_adversarios):
        print(f"\n--- INICIANDO GERAÇÃO DE PDF (ID {player_id}) ---")
        
        # 1. Puxar Inteligência de Negócio
        print("[1/4] Extraindo métricas do motor analítico...")
        dados_scout = self.motor.gerar_raio_x_jogador(player_id)
        if "erro" in dados_scout:
            print(f"Erro Crítico: {dados_scout['erro']}")
            return
            
        # 2. Gerar Visualizações (Data Viz B2B)
        print("[2/4] Desenhando gráficos premium...")
        grafico_spark = self.estudio.gerar_sparkline_evolucao(dados_scout['historico_completo'], player_id)
        grafico_gauss = self.estudio.gerar_gaussiana(dados_scout['gaussiana_media_idade'], dados_scout['gaussiana_std_idade'], dados_scout['elo_global_atual'], player_id)
        grafico_radar = self.estudio.gerar_radar_superficies(dados_scout['elo_saibro'], dados_scout['elo_hard'], dados_scout['elo_grass'], player_id)
        
        dados_scout['caminho_spark'] = f"file://{grafico_spark}"
        dados_scout['caminho_gauss'] = f"file://{grafico_gauss}"
        dados_scout['caminho_radar'] = f"file://{grafico_radar}"
        
        # 3. Rodar as Simulações da Inteligência Artificial (Bola de Cristal)
        print("[3/4] Calculando Head-to-Heads Preditivos (XGBoost)...")
        lista_simulacoes = []
        for adv in benchmark_adversarios:
            res = self.motor.simular_confronto_ia(player_id, adv['id'], superficie=adv['piso'])
            
            # Tratamento de erro caso o ID do adversário não exista na base
            if "erro" not in res:
                lista_simulacoes.append({
                    "adversario": res['jogador_b'],
                    "contexto": f"{adv['contexto']} - {adv['piso']}",
                    "probabilidade": res['probabilidade_vitoria_a']
                })
            else:
                lista_simulacoes.append({
                    "adversario": f"ID {adv['id']} Inválido",
                    "contexto": "Erro de Base de Dados",
                    "probabilidade": 0.0
                })
                
        dados_scout['simulacoes'] = lista_simulacoes
        
        # 4. Injetar no HTML e Compilar PDF
        print("[4/4] Renderizando HTML e compilando PDF via WeasyPrint...")
        template = self.env.get_template('relatorio_individual.html')
        html_renderizado = template.render(dados_scout)
        
        caminho_html_temp = os.path.join(self.pasta_outputs, f"temp_{player_id}.html")
        with open(caminho_html_temp, 'w', encoding='utf-8') as f:
            f.write(html_renderizado)
            
        caminho_pdf = os.path.join(self.pasta_outputs, f"Scout_{dados_scout['nome'].replace(' ', '_')}.pdf")
        
        HTML(string=html_renderizado, base_url=self.diretorio_atual).write_pdf(caminho_pdf)
        os.remove(caminho_html_temp)
        
        print(f"\n--- SUCESSO ABSOLUTO! ---")
        print(f"Relatório executivo gerado em: {caminho_pdf}")

# ==========================================
# TESTE FINAL: A HORA DA VERDADE
# ==========================================
if __name__ == "__main__":
    construtor = ConstrutorRelatorio(chave='W')
    
    # Nosso Atleta Alvo
    id_alvo = "800655335" # Victoria Barros
    
    # IMPORTANTE: Troque estes IDs de adversárias pelos IDs REAIS que existam 
    # dentro da sua base de dados 'dim_players_W.csv'. 
    # Caso contrário, o sistema vai colocar "ID Inválido" no PDF.
    cenarios_h2h = [
        {"id": "800591535", "piso": "Saibro", "contexto": "Rival Direta (Mesma Idade)"},
        {"id": "800644962", "piso": "Piso Duro", "contexto": "Top 10 Mundial (Teste de Fogo)"},
        {"id": "800601474", "piso": "Saibro", "contexto": "Atleta Mais Velha (Experiência)"}
    ]
    
    construtor.gerar_relatorio_individual(id_alvo, cenarios_h2h)