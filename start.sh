#!/usr/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
screen -S TTS -d -m $SHELL -c "cd $SCRIPT_DIR; source ./venv/bin/activate; python3.10 -m TTS_bad"
