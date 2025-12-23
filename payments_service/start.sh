#!/bin/bash

sleep 10

python -c "from app.db.init_db import init_db; init_db()" 

exec uvicorn app.main:app --host 0.0.0.0 --port 8002