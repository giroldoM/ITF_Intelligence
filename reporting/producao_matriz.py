import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from motor_inteligencia import MotorInteligencia

# ==========================================
# LISTA DE PRODUÇÃO PARA MATRIZES GIGANTES
# Formato: ("ID_DO_JOGADOR", "GÊNERO")
# 'W' = Feminino | 'M' = Masculino
# ==========================================
LISTA_MATRIZ = [
    ("800684304","M"), #Henrique Queiroz
    ("800716347","M"), #Livas Damazio
    ("800680259","M"), #Luis Guto Miguel
    ("800695229","M"), #Lucas Moscatto
    ("800695060","W"), #Nauhany Silva
    ("800642706","M"), #Pedro DIETRICH
    ("800655734", "W"), # Pietra Rivoli 
    ("800695229", "M"), # Lucas Moscatto 
    ("800676504","M"), #Leonardo Storck
    ("800696001","M"), #Cadu Lino
    ("800678202","M"), #GENERICO MASCULINO
    ("800662814","W"), #GENERICO FEMININO
]
# ==========================================

class FabricaMatrizes:
    def __init__(self):
        print("--- INICIANDO FÁBRICA DE MATRIZES (MODO MISTO) ---")
        
        # Carregando os dois motores em paralelo para otimizar velocidade
        print("[Carregando Motor Feminino...]")
        self.motor_w = MotorInteligencia(chave='W')
        print("[Carregando Motor Masculino...]")
        self.motor_m = MotorInteligencia(chave='M')
        
        self.diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        self.pasta_templates = os.path.join(self.diretorio_atual, 'templates')
        self.env = Environment(loader=FileSystemLoader(self.pasta_templates))
        
        # Cria a pasta do dia
        data_hoje = datetime.now().strftime('%Y-%m-%d')
        self.pasta_destino = os.path.join(self.diretorio_atual, 'outputs', data_hoje)
        os.makedirs(self.pasta_destino, exist_ok=True)
        print(f"\n[+] Diretório de saída configurado: {self.pasta_destino}")

    def processar_lote(self, lista_ids):
        total = len(lista_ids)
        for i, (player_id, genero) in enumerate(lista_ids, 1):
            print(f"\n[{i}/{total}] Processando Matriz para Atleta ID: {player_id} ({genero})")
            
            # Escolhe o cérebro certo com base na tupla
            motor_ativo = self.motor_w if genero.upper() == 'W' else self.motor_m
            self._gerar_pdf_unico(player_id, motor_ativo)
            
        print(f"\n--- LOTE DE MATRIZES CONCLUÍDO! {total} PDFs gerados com sucesso na pasta de hoje. ---")

    def _gerar_pdf_unico(self, player_id, motor):
        dados_matriz = motor.gerar_matriz_confrontos(player_id)
        
        if not dados_matriz:
            print(f"  -> ERRO: Não foi possível gerar a matriz para o ID {player_id} (Pulando...)")
            return
            
        print(f"  -> Renderizando HTML para {dados_matriz['nome_jogador']} (Isto pode levar alguns segundos)...")
        template = self.env.get_template('matriz_confrontos.html')
        html_renderizado = template.render(dados_matriz)
        
        # Adicionei o ID no nome do arquivo para evitar sobrescrever se tiver homônimos
        nome_arquivo = f"Matriz_Global_{dados_matriz['nome_jogador'].replace(' ', '_')}_{player_id}.pdf"
        caminho_pdf = os.path.join(self.pasta_destino, nome_arquivo)
        
        print(f"  -> Compilando dezenas de páginas em PDF...")
        HTML(string=html_renderizado, base_url=self.diretorio_atual).write_pdf(caminho_pdf)
        print(f"  -> Sucesso: {nome_arquivo}")

if __name__ == "__main__":
    fabrica = FabricaMatrizes()
    if LISTA_MATRIZ:
        fabrica.processar_lote(LISTA_MATRIZ)
    else:
        print("A lista de jogadores (LISTA_MATRIZ) está vazia. Adicione IDs para rodar.")