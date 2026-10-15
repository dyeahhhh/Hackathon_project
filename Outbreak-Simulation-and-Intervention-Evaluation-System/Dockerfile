FROM python:3.11-slim

WORKDIR /app

COPY outbreak_backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY outbreak_backend ./outbreak_backend
COPY outbreak ./outbreak

EXPOSE 8000

CMD ["python", "-m", "outbreak", "run", "--host", "0.0.0.0", "--port", "8000"]
