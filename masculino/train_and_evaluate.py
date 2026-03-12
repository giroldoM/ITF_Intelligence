import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, roc_auc_score
from sklearn.calibration import CalibratedClassifierCV

print("--- INICIANDO FASE 4: TREINO E CALIBRAÇÃO DO XGBOOST ---")

# 1. Carregar o Dataset
ficheiro_ml = "dataset_ml_final.csv"
print(f"A carregar o dataset {ficheiro_ml}...")
df = pd.read_csv(ficheiro_ml)

# 2. O Split Temporal (Caminhada no Tempo)
# Treino: 2023 e 2024 | Teste: 2025 e 2026
df_train = df[df['Year'] <= 2024].copy()
df_test = df[df['Year'] >= 2025].copy()

features = ['elo_diff', 'surface_elo_diff', 'age_diff']
target = 'target'

X_train = df_train[features]
y_train = df_train[target]

X_test = df_test[features]
y_test = df_test[target]

print(f"\nDistribuição do Split Temporal:")
print(f" -> Treino (2023-2024): {len(X_train)} jogos")
print(f" -> Teste (2025-2026): {len(X_test)} jogos")

# 3. Configuração e Treino do XGBoost Base
print("\nA treinar o modelo XGBoost Base...")
# Hiperparâmetros conservadores para evitar overfitting num desporto ruidoso
xgb_model = xgb.XGBClassifier(
    n_estimators=150,
    learning_rate=0.05,
    max_depth=4,
    min_child_weight=3,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='logloss'
)

xgb_model.fit(X_train, y_train)

# 4. Calibração (Platt Scaling)
# O CalibratedClassifierCV vai fazer uma validação cruzada interna no Treino 
# para ajustar a curva sigmoide (Regressão Logística) por cima do XGBoost
print("A calibrar as probabilidades com Platt Scaling (Logistic)...")
calibrated_xgb = CalibratedClassifierCV(xgb_model, method='sigmoid', cv=5)
calibrated_xgb.fit(X_train, y_train)

# 5. Predições no Conjunto de Teste (Ver o Futuro)
print("\nA fazer predições para 2025 e 2026...")
# Predições brutas do XGBoost
y_pred_proba_raw = xgb_model.predict_proba(X_test)[:, 1]

# Predições calibradas
y_pred_proba_cal = calibrated_xgb.predict_proba(X_test)[:, 1]
y_pred_class = calibrated_xgb.predict(X_test)

# 6. Avaliação de Métricas
print("\n==================================================")
print("             MÉTRICAS DE DESEMPENHO")
print("==================================================")

acc = accuracy_score(y_test, y_pred_class)
auc = roc_auc_score(y_test, y_pred_proba_cal)

# Brier Score: A métrica suprema (quão mais perto de 0, melhor a calibração)
brier_raw = brier_score_loss(y_test, y_pred_proba_raw)
brier_cal = brier_score_loss(y_test, y_pred_proba_cal)

# Log Loss: Penaliza severamente quando o modelo tem muita certeza e erra
ll_raw = log_loss(y_test, y_pred_proba_raw)
ll_cal = log_loss(y_test, y_pred_proba_cal)

print(f"Acurácia (Acertos de Vencedor): {acc:.2%}")
print(f"ROC AUC (Capacidade de Distinção): {auc:.4f}")
print("-" * 50)
print(f"Brier Score (Bruto):      {brier_raw:.4f}")
print(f"Brier Score (Calibrado):  {brier_cal:.4f} <- (O nosso objetivo!)")
print("-" * 50)
print(f"Log Loss (Bruto):         {ll_raw:.4f}")
print(f"Log Loss (Calibrado):     {ll_cal:.4f}")
print("==================================================")

# 7. Importância das Features (O que o modelo achou mais relevante?)
print("\nImportância das Features (XGBoost Base):")
importances = xgb_model.feature_importances_
for col, imp in zip(features, importances):
    print(f" -> {col}: {imp:.2%}")

# =========================================================
# 8. EXPORTAÇÃO DO MODELO (A PONTE PARA O RELATÓRIO)
# =========================================================
print("\nA exportar o modelo treinado para o motor de relatórios...")
caminho_modelo = "xgb_model_M.json"
xgb_model.save_model(caminho_modelo)
print(f"[+] Modelo exportado com sucesso para: {caminho_modelo}")