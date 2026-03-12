import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from motor_inteligencia import MotorInteligencia
from gerador_graficos import EstudioGrafico

# ==========================================
# LISTA DE PRODUÇÃO MISTA
# Formato: ("ID_DO_JOGADOR", "GÊNERO")
# 'W' = Feminino | 'M' = Masculino
# ==========================================
LISTA_JOGADORES = [
    ("800680259", "M"), # Victoria Barros
    # ("COLOQUE_O_ID_DO_MENINO_AQUI", "M"), 
    # ("OUTRA_MENINA", "W"),
]
# ==========================================

class FabricaRelatorios:
    def __init__(self):
        print("--- INICIANDO FÁBRICA DE RELATÓRIOS (MODO MISTO) ---")
        
        # Carregando os dois motores em paralelo
        print("[Carregando Motor Feminino...]")
        self.motor_w = MotorInteligencia(chave='W')
        print("[Carregando Motor Masculino...]")
        self.motor_m = MotorInteligencia(chave='M')
        
        self.estudio = EstudioGrafico()
        
        self.diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.pasta_templates = os.path.join(self.diretorio_atual, 'templates')
        self.env = Environment(loader=FileSystemLoader(self.pasta_templates))
        
        # Criar pasta estruturada por data: outputs/YYYY-MM-DD/
        data_hoje = datetime.now().strftime('%Y-%m-%d')
        self.pasta_destino = os.path.join(self.diretorio_atual, 'outputs', data_hoje)
        os.makedirs(self.pasta_destino, exist_ok=True)
        print(f"\n[+] Diretório de saída configurado: {self.pasta_destino}\n")

    def processar_lote(self, lista_ids):
        total = len(lista_ids)
        for i, (player_id, genero) in enumerate(lista_ids, 1):
            print(f"[{i}/{total}] Processando Atleta ID: {player_id} ({genero})")
            
            # Escolhe o cérebro certo com base na tupla
            motor_ativo = self.motor_w if genero.upper() == 'W' else self.motor_m
            
            self._gerar_pdf_unico(player_id, motor_ativo)
            
        print(f"\n--- LOTE CONCLUÍDO! {total} PDFs gerados com sucesso. ---")

    def _gerar_pdf_unico(self, player_id, motor):
        # 1. Dados do Atleta
        dados_scout = motor.gerar_raio_x_jogador(player_id)
        if "erro" in dados_scout:
            print(f"  -> ERRO: {dados_scout['erro']} (Pulando...)")
            return
            
        # 2. Gráficos Premium
        c_spark = self.estudio.gerar_sparkline_evolucao(dados_scout['historico_completo'], player_id)
        c_gauss = self.estudio.gerar_gaussiana(dados_scout['gaussiana_media_idade'], dados_scout['gaussiana_std_idade'], dados_scout['elo_global_atual'], player_id)
        c_radar = self.estudio.gerar_radar_superficies(dados_scout['elo_saibro'], dados_scout['elo_hard'], dados_scout['elo_grass'], player_id)
        
        dados_scout['caminho_spark'] = f"file://{c_spark}"
        dados_scout['caminho_gauss'] = f"file://{c_gauss}"
        dados_scout['caminho_radar'] = f"file://{c_radar}"
        
        # 3. H2H Dinâmico e Automático
        cenarios_h2h = motor.buscar_adversarios_dinamicos(player_id, dados_scout)
        lista_simulacoes = []
        for adv in cenarios_h2h:
            res = motor.simular_confronto_ia(player_id, adv['id'], superficie=adv['piso'])
            if "erro" not in res:
                lista_simulacoes.append({
                    "adversario": res['jogador_b'],
                    "contexto": adv['contexto'],
                    "probabilidade": res['probabilidade_vitoria_a']
                })
        dados_scout['simulacoes'] = lista_simulacoes
        
        # 4. Compilar PDF
        template = self.env.get_template('relatorio_individual.html')
        html_renderizado = template.render(dados_scout)
        
        nome_arquivo = f"{dados_scout['nome'].replace(' ', '_')}_{dados_scout['id']}.pdf"
        caminho_pdf = os.path.join(self.pasta_destino, nome_arquivo)
        
        HTML(string=html_renderizado, base_url=self.diretorio_atual).write_pdf(caminho_pdf)
        print(f"  -> Sucesso: {nome_arquivo}")

if __name__ == "__main__":
    fabrica = FabricaRelatorios()
    fabrica.processar_lote(LISTA_JOGADORES)