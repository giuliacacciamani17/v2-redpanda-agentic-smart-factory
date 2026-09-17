import os


KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "localhost:29092",
)

TELEMETRY_TOPIC = os.getenv(
    "TELEMETRY_TOPIC",
    "factory.telemetry",
)

MACHINE_STATE_TOPIC = os.getenv(
    "MACHINE_STATE_TOPIC",
    "factory.machine-state",
)

MACHINE_ID = os.getenv(
    "MACHINE_ID",
    "machine-01",
)

#secondi di attesa tra un evento telemetrico e l'altro
EVENT_INTERVAL_SECONDS = float(
    os.getenv(
        "EVENT_INTERVAL_SECONDS",
        "2",
    )
)

#quanti secondi si cerca l’ultimo stato della macchina
STATE_READ_TIMEOUT_SECONDS = float(
    os.getenv(
        "STATE_READ_TIMEOUT_SECONDS",
        "2",
    )
)

RANDOM_SEED = int(
    os.getenv(
        "RANDOM_SEED",
        "42",
    )
)

CORRELATION_PREFIX = os.getenv(
    "CORRELATION_PREFIX",
    "abc",
)

CORRELATION_START = int(
    os.getenv(
        "CORRELATION_START",
        "123",
    )
)


def validate_configuration() -> None:
    if not KAFKA_BROKER.strip():
        raise ValueError(
            "KAFKA_BROKER non puo essere vuoto"
        )

    if not TELEMETRY_TOPIC.strip():
        raise ValueError(
            "TELEMETRY_TOPIC non puo essere vuoto"
        )

    if not MACHINE_STATE_TOPIC.strip():
        raise ValueError(
            "MACHINE_STATE_TOPIC non puo essere vuoto"
        )

    if not MACHINE_ID.strip():
        raise ValueError(
            "MACHINE_ID non puo essere vuoto"
        )

    if EVENT_INTERVAL_SECONDS < 0:
        raise ValueError(
            "EVENT_INTERVAL_SECONDS non puo "
            "essere negativo"
        )

    if STATE_READ_TIMEOUT_SECONDS <= 0:
        raise ValueError(
            "STATE_READ_TIMEOUT_SECONDS deve "
            "essere maggiore di zero"
        )

    if CORRELATION_START < 0:
        raise ValueError(
            "CORRELATION_START non puo "
            "essere negativo"
        )