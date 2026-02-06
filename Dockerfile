FROM python:3.12

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 6519

CMD ["python3", "app.py"]
