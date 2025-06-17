# 📈 Options Trading Bot

A Python-based machine learning pipeline for predicting short-term movements in call option contracts.

## 🚀 Project Goals

- Collect real options chain data across multiple tickers and expirations
- Engineer relevant features (e.g., moneyness, days to expiration)
- Train and evaluate ML models to classify profitable opportunities
- Prepare for real-time predictions and potential paper/live trading

## 📂 Project Structure

options-trading-bot:
- data: Raw and processed options data
- models: Saved trained models
- notebooks: Jupyter notebooks for EDA and modeling
- scripts: Data ingestion and automation scripts
- utils: Reusable functions
- journey: Archived development steps
- requirements.txt
- README.md

## 📊 Example Model Output

- Logistic Regression w/ class balancing
- Precision: 0.33 | Recall: 0.83 | F1: 0.48 (for class 1: profitable trades)
- Confusion Matrix:

          Predicted
       |   0   |   1
    ---|-------|------
Actual 0 | 30 | 10
Actual 1 | 1 | 5

## 📚 Notebooks

- `feature_engineering.ipynb` – creates model-ready features
- `model_baseline.ipynb` – trains logistic regression classifier

## 🧠 Next Steps

- Move to XGBoost or LightGBM
- Integrate real-time prediction script
- Add backtesting and alert logic
- Deploy model and share predictions

## 🤝 Collaborators

- Shahzeb Narsi
- Sumair Saleem

---

Feel free to clone, fork, or contribute!
