web: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
worker: celery -A worker.celery_app worker --loglevel=info
