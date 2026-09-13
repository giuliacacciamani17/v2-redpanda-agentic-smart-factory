#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COUNTER_FILE="$PROJECT_ROOT/.next-correlation-id"

EVENTS_PER_BLOCK=5
INITIAL_CORRELATION_ID=123

cd "$PROJECT_ROOT"

if [ ! -f "$COUNTER_FILE" ]; then
    printf '%s\n' "$INITIAL_CORRELATION_ID" > "$COUNTER_FILE"
fi

CORRELATION_START="$(cat "$COUNTER_FILE")"

if ! [[ "$CORRELATION_START" =~ ^[0-9]+$ ]]; then
    echo "Errore: il contatore deve contenere un numero intero."
    exit 1
fi

CORRELATION_END=$((CORRELATION_START + EVENTS_PER_BLOCK - 1))
RANDOM_SEED=$((CORRELATION_START * 17 + 31))

echo "Generazione del blocco:"
echo "Correlation ID: abc-$CORRELATION_START -> abc-$CORRELATION_END"
echo "Random seed: $RANDOM_SEED"

docker compose run --rm --no-deps \
    -e CORRELATION_START="$CORRELATION_START" \
    -e RANDOM_SEED="$RANDOM_SEED" \
    machine-simulator

NEXT_CORRELATION_START=$((CORRELATION_START + EVENTS_PER_BLOCK))

printf '%s\n' "$NEXT_CORRELATION_START" > "$COUNTER_FILE"

echo "Blocco completato."
echo "Prossimo blocco da abc-$NEXT_CORRELATION_START"