# 🎓 RAG برای دانشگاه پیام نور

دستیار هوشمند مبتنی بر RAG برای پاسخ به سوالات دانشجویان.

## نصب و اجرا
```bash
pip install -r requirements.txt
python -m src.ingestion
python run_api.py
streamlit run src/web_ui.py
