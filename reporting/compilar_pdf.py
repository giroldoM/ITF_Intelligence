import os
from jinja2 import Environment, FileSystemLoader
from motor_inteligencia import MotorInteligencia
from gerador_graficos import EstudioGrafico
from weasyprint import HTML

class ConstrutorRelatorio:
    def __init__(self, chave='M'):
        self.motor = MotorInteligencia(chave=chave)
        self.estudio = EstudioGrafico()
        
        # Configurar caminhos
        self.diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.pasta_templates = os.path.join(self.diretorio_atual, 'templates')
        self.pasta_outputs = os.path.join(self.diretorio_atual, 'outputs')
        
        # Iniciar o motor do Jinja2 para ler o HTML
        self.env = Environment(loader=FileSystemLoader(self.pasta_templates))
    
    def gerar_relatorio_individual(self, player_id):
        print(f"\n--- INICIANDO GERAÇÃO DE PDF PARA ID {player_id} ---")
        
        # 1. Puxar as métricas de negócio
        print("1. Extraindo inteligência...")
        dados_scout = self.motor.gerar_raio_x_jogador(player_id)
        
        if "erro" in dados_scout:
            print(f"Erro: {dados_scout['erro']}")
            return
            
        # 2. Gerar os gráficos
        print("2. Desenhando gráficos...")
        grafico_evo = self.estudio.gerar_grafico_evolucao(dados_scout['historico_completo'], player_id)
        grafico_surf = self.estudio.gerar_grafico_superficie(dados_scout['elo_saibro'], dados_scout['elo_hard'], player_id)
        
        # Adicionar os caminhos absolutos das imagens (O WeasyPrint lê diretórios locais perfeitamente)
        dados_scout['caminho_grafico_evolucao'] = f"file://{grafico_evo}"
        dados_scout['caminho_grafico_superficie'] = f"file://{grafico_surf}"
        
        # 3. Injetar dados no HTML
        print("3. Injetando dados no Template...")
        template = self.env.get_template('relatorio_individual.html')
        html_renderizado = template.render(dados_scout)
        
        caminho_html_temp = os.path.join(self.pasta_outputs, f"temp_{player_id}.html")
        with open(caminho_html_temp, 'w', encoding='utf-8') as f:
            f.write(html_renderizado)
            
        # 4. Converter HTML para PDF com WeasyPrint
        print("4. Compilando PDF...")
        caminho_pdf = os.path.join(self.pasta_outputs, f"Scouting_Report_{dados_scout['nome'].replace(' ', '_')}.pdf")
        
        # A mágica do WeasyPrint numa linha só
        HTML(string=html_renderizado, base_url=self.diretorio_atual).write_pdf(caminho_pdf)
        
        # Limpar o HTML temporário
        os.remove(caminho_html_temp)
        
        print(f"--- SUCESSO! PDF GERADO: {caminho_pdf} ---")

# --- TESTE FINAL ---
if __name__ == "__main__":
    # Vamos gerar o relatório da Victoria Barros (Chave Feminina)
    construtor = ConstrutorRelatorio(chave='W')
    construtor.gerar_relatorio_individual("800655335")