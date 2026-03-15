#!/usr/bin/env sh

export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"

exec rq worker --url redis://redis:6379
