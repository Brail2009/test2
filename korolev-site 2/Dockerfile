FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 site
COPY --chown=site:site . .
RUN mkdir -p storage static/img/uploads && chown -R site:site storage static/img/uploads
USER site
EXPOSE 5001
CMD ["gunicorn", "-c", "gunicorn.conf.py", "--bind", "0.0.0.0:5001", "wsgi:app"]
