FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY config.py main.py policy.py risk_engine.py state.py ./

CMD ["python", "main.py"]