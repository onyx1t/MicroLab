FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./start.sh /app/start.sh

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
