# 📈 Options Trading Bot

This project is an early-stage attempt at building a machine learning-driven options trading bot. It collects and engineers options market data to make intelligent predictions about whether a given option will expire **in-the-money (ITM)** or **out-of-the-money (OTM)**.

It’s built with flexibility in mind, allowing for multi-ticker support, automation-ready design, and modular pipelines for future integration with paper trading and live execution systems.

---

## 🚀 Project Goals

- ✅ Collect historical options chain data from Yahoo Finance
- ✅ Engineer features like moneyness, time to expiration, and volatility metrics
- ✅ Train a baseline classifier to predict ITM/OTM options
- 🔄 [In Progress] Add more complex models like XGBoost and ensemble methods
- 🔜 Automate workflows and enable signal-based paper trading (via Alpaca/n8n)
- 🔜 Visualize live metrics and performance in a clean dashboard

---

## ⚙️ Tech Stack

- **Python 3.10+**
- `yfinance`, `pandas`, `scikit-learn`, `matplotlib`
- Jupyter Notebooks
- Git + GitHub for version control
- Virtual Environment (via `venv`)

---

## 📁 Folder Structure

options-trading-bot/
- data/ # Raw or processed options data
- models/ # Trained models (pickle/joblib)
- notebooks/ # Jupyter notebooks for dev
   - data_collection.ipynb
   - feature_engineering.ipynb
   - model_baseline.ipynb
- scripts/ # Reusable Python scripts (to be refactored from notebooks)
   - data_loader.py
   - feature_engineering.py
   - train_model.py
- images/ # Visual outputs (confusion matrix, ROC curves, etc.)
- requirements.txt # Python dependencies
- README.md # You're reading it.