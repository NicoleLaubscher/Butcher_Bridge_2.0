#!/usr/bin/env sh
set -eu
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
test -f .env || cp .env.demo.example .env
python seed.py --reset
python run.py

