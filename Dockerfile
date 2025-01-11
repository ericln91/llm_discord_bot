FROM python:3.12.8-slim-bullseye

WORKDIR /app

COPY botv1.1.py requirements.txt .

SHELL ["/bin/bash", "-c"]

RUN python -m venv disc-bot
RUN . /app/disc-bot/bin/activate

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m appuser
USER appuser

CMD ["python","botv1.1.py"]
