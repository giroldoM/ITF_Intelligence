import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, roc_auc_score

print("--- TREINO E AVALIAÇÃO DO XGBOOST (FEMININO) ---")

df = pd.read_csv("dataset_ml_final_W.csv")

df_train = df[df['Year'] <= 2024]
df_test = df[df['Year'] >= 2025]

features = ['elo_diff', 'surface_elo_diff', 'age_diff']
X_train, y_train = df_train[features], df_train['target']
X_test, y_test = df_test[features], df_test['target']

xgb_model = xgb.XGBClassifier(
    n_estimators=150, learning_rate=0.05, max_depth=4,
    min_child_weight=3, subsample=0.8, colsample_bytree=0.8, random_state=42
)
xgb_model.fit(X_train, y_train)

y_pred_proba = xgb_model.predict_proba(X_test)[:, 1]
y_pred_class = xgb_model.predict(X_test)

print("\n--- MÉTRICAS FEMININO ---")
print(f"Acurácia: {accuracy_score(y_test, y_pred_class):.2%}")
print(f"ROC AUC:  {roc_auc_score(y_test, y_pred_proba):.4f}")
print(f"Brier Score: {brier_score_loss(y_test, y_pred_proba):.4f}")
print(f"Log Loss: {log_loss(y_test, y_pred_proba):.4f}")

print("\n--- IMPORTÂNCIA DAS FEATURES ---")
for col, imp in zip(features, xgb_model.feature_importances_):
    print(f"{col}: {imp:.2%}")