#!/usr/bin/env bash
# Bot siempre encendido en tu PC o servidor (respuesta inmediata en Telegram).
# 1) Copia .env.ejemplo a .env y llénalo.  2) bash run_local.sh
set -a; source .env; set +a
export GIT_PUSH=1
python3 -m agents.bot loop
