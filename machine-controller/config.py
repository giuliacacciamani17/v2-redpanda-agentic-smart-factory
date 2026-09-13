import os


KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "localhost:29092",
)

COMMANDS_TOPIC = os.getenv(
    "COMMANDS_TOPIC",
    "factory.commands",
)

COMMAND_RESULTS_TOPIC = os.getenv(
    "COMMAND_RESULTS_TOPIC",
    "factory.command-results",
)

MACHINE_STATE_TOPIC = os.getenv(
    "MACHINE_STATE_TOPIC",
    "factory.machine-state",
)

CONSUMER_GROUP = os.getenv(
    "CONSUMER_GROUP",
    "machine-controller-group-v2",
)

CONTROLLER_ID = os.getenv(
    "CONTROLLER_ID",
    "machine-controller-01-v2",
)

CONTROLLER_MODE = os.getenv(
    "CONTROLLER_MODE",
    "MIXED",
).upper()