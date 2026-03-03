FROM python:3.12-slim

# Keeps Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy BOTH vital files to the server
COPY main.py .
COPY agent.py .

EXPOSE 8000

CMD sh -c "${START_COMMAND:-uvicorn main:CMD python agent.py dev & uvicorn main:app --host 0.0.0.0 --port 800}"
