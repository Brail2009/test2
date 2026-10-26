import os
bind=os.getenv('GUNICORN_BIND','127.0.0.1:5001')
# Один процесс: файловый редактор контента без конфликтов записи.
workers=1
threads=1
worker_class='sync'
timeout=60
accesslog='-'
errorlog='-'
loglevel='info'
