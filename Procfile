web: gunicorn main:app -b 0.0.0.0:$PORT
worker: celery -A main.celery_app worker --loglevel=info
playwright: ./post_install.sh 