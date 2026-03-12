import os
import subprocess
import time

class TorreDeControlo:
    def __init__(self):
        self.diretorio_raiz = os.path.dirname(os.path.abspath(__file__))
        print("==================================================")
        print("  INICIANDO PIPELINE SEMANAL DE ATUALIZAÇÃO B2B")
        print("==================================================\n")

    def rodar_comando(self, script, pasta):
        """Simula o 'cd pasta' e roda o 'python script.py'"""
        caminho_pasta = os.path.join(self.diretorio_raiz, pasta)
        print(f"\n>>> [{pasta.upper()}] Iniciando: {script} ...")
        
        # O argumento cwd (Current Working Directory) faz o papel do 'cd' automaticamente
        resultado = subprocess.run(["python", script], cwd=caminho_pasta)
        
        if resultado.returncode != 0:
            print(f" [X] ERRO CRÍTICO: Falha ao executar {script} em {pasta}.")
            print(" Pipeline interrompido para evitar corrupção de dados.")
            return False
        
        print(f" [V] SUCESSO: {script} concluído.")
        return True

    def executar_circuito(self, pasta, scripts_ordem):
        print(f"\n--- INICIANDO CIRCUITO {pasta.upper()} ---")
        for script in scripts_ordem:
            sucesso = self.rodar_comando(script, pasta)
            if not sucesso:
                return False # Para tudo se um script falhar
            time.sleep(2) # Pausa de 2 segundos para o SO respirar entre scripts
        return True

if __name__ == "__main__":
    torre = TorreDeControlo()
    
    # =====================================================================
    # ORDEM CRONOLÓGICA DE EXECUÇÃO (O "Domingo de Manutenção")
    # =====================================================================
    # IMPORTANTE: Verifique se os nomes dos arquivos batem com os que 
    # você tem nas pastas (ex: 'extrator_partidas.py' vs 'scraper_partidas.py')
    
    scripts_masculino = [
        "extrator_partidas.py",    # 1. Passado: Puxa partidas finais de quem vai cair/fazer 18 anos
        "pegar_ids.py",            # 2. Presente: Baixa o novo Ranking Oficial Top 4000
        "extrator_partidas.py",    # 3. Futuro: Roda de novo para puxar o histórico dos calouros recém-descobertos
        "elo_core.py",             # 4. Big Bang: Recalcula todos os Elos desde 2021
        "features_builder.py",     # 5. Estrutura: Monta o dataset final com as features
        "train_and_evaluate.py"    # 6. Oráculo: Retreina o modelo XGBoost com a nova semana
    ]
    
    scripts_feminino = [
        "scraper_partidas.py",     # 1. Passado (Igual acima, mas com os nomes da pasta W)
        "scraper_top4000.py",      # 2. Presente
        "scraper_partidas.py",     # 3. Futuro
        "elo_core.py",             # 4. Big Bang
        "features_builder.py",     # 5. Estrutura
        "train_and_evaluate.py"    # 6. Oráculo
    ]
    
    # Executa primeiro os Homens, depois as Mulheres
    if torre.executar_circuito("masculino", scripts_masculino):
        if torre.executar_circuito("feminino", scripts_feminino):
            print("\n==================================================")
            print(" PIPELINE SEMANAL CONCLUÍDO COM SUCESSO ABSOLUTO!")
            print(" Os relatórios individuais e matrizes já podem ser gerados.")
            print("==================================================")