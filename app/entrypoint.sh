#!/bin/sh
wait-for-it db:5432 -t 10
flask db upgrade
waitress-serve --host 0.0.0.0 --port 5000 app:app
wait-for-it -t 10 db:5432 && \
flask db upgrade && \
waitress-serve --host 0.0.0.0 --port 5000 app:app
