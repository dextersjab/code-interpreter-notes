#!/bin/bash
ulimit -n 1024
ulimit -v $PROCESS_MEMORY_LIMIT
cd $HOME/.openai_internal/
exec tini -- python3 -m uvicorn --host 0.0.0.0 --port 8080 user_machine.app:app