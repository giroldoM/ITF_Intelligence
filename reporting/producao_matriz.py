import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from motor_inteligencia import MotorInteligencia

# ==========================================
# ID PARA A MATRIZ GIGANTE
# ==========================================
ID_ALVO = "800655734"  # Substitua pelo ID do Guto ou outro
GENERO = "W"           # 'M' ou 'W'
# ==========================================

print(f"--- INICIANDO MATRIZ DE CONFRONTOS ---")
motor = MotorInteligencia(chave=GENERO)

dados_matriz = motor.gerar_matriz_confrontos(ID_ALVO)

if dados_matriz:
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    env = Environment(loader=FileSystemLoader(os.path.join(diretorio_atual, 'templates')))
    
    pasta_destino = os.path.join(diretorio_atual, 'outputs', datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(pasta_destino, exist_ok=True)
    
    print("[+] Renderizando o HTML (Isto pode levar alguns segundos devido ao volume de dados)...")
    template = env.get_template('matriz_confrontos.html')
    html_renderizado = template.render(dados_matriz)
    
    nome_arquivo = f"Matriz_Global_{dados_matriz['nome_jogador'].replace(' ', '_')}.pdf"
    caminho_pdf = os.path.join(pasta_destino, nome_arquivo)
    
    print("[+] Compilando as dezenas de páginas em PDF...")
    HTML(string=html_renderizado, base_url=diretorio_atual).write_pdf(caminho_pdf)
    
    print(f"\n--- SUCESSO! Matriz gerada: {caminho_pdf} ---")
else:
    print("ERRO: Não foi possível gerar a matriz para este jogador.")