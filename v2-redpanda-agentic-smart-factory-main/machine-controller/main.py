import json
import signal
import uuid
from datetime import datetime, timezone
from typing import Any

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Producer,
)

from config import (
    COMMAND_RESULTS_TOPIC,
    COMMANDS_TOPIC,
    CONSUMER_GROUP,
    CONTROLLER_ID,
    CONTROLLER_MODE,
    KAFKA_BROKER,
    MACHINE_STATE_TOPIC,
)
from controller import (
    SUCCESS,
    MachineController,
)


REQUIRED_COMMAND_FIELDS = {
    "command_id",
    "decision_id",
    "correlation_id",
    "machine_id",
    "action",
    "risk_score",
    "current_speed",
    "target_speed",
}

running = True


def create_consumer() -> Consumer:
    configuration = {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }

    return Consumer(configuration)


def create_producer() -> Producer:
    configuration = {
        "bootstrap.servers": KAFKA_BROKER,
        "client.id": CONTROLLER_ID,
    }

    return Producer(configuration)


def deserialize_command(
    message_value: bytes,
) -> dict[str, Any]:
    command = json.loads(
        message_value.decode("utf-8")
    )

    if not isinstance(command, dict):
        raise TypeError(
            "Il comando deve essere un oggetto JSON"
        )

    missing_fields = (
        REQUIRED_COMMAND_FIELDS
        - command.keys()
    )

    if missing_fields:
        missing_names = ", ".join(
            sorted(missing_fields)
        )

        raise ValueError(
            f"Campi mancanti: {missing_names}"
        )

    validate_command_values(command)

    return command


def validate_command_values(
    command: dict[str, Any],
) -> None:
    string_fields = {
        "command_id",
        "decision_id",
        "correlation_id",
        "machine_id",
        "action",
    }

    for field_name in string_fields:
        if not isinstance(
            command[field_name],
            str,
        ):
            raise TypeError(
                f"{field_name} deve essere "
                "una stringa"
            )

        if not command[field_name].strip():
            raise ValueError(
                f"{field_name} non puo essere vuoto"
            )

    try:
        command["risk_score"] = float(
            command["risk_score"]
        )

        command["current_speed"] = int(
            command["current_speed"]
        )

        command["target_speed"] = int(
            command["target_speed"]
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "risk_score, current_speed e "
            "target_speed devono essere numerici"
        ) from error

    if not 0 <= command["risk_score"] <= 1:
        raise ValueError(
            "risk_score deve essere compreso "
            "tra 0 e 1"
        )

    if command["current_speed"] < 0:
        raise ValueError(
            "current_speed non puo essere negativo"
        )

    if command["target_speed"] < 0:
        raise ValueError(
            "target_speed non puo essere negativo"
        )


def create_command_result(
    command: dict[str, Any],
    execution_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "result_id": str(uuid.uuid4()),
        "command_id": command["command_id"],
        "decision_id": command["decision_id"],
        "correlation_id": command[
            "correlation_id"
        ],
        "controller_id": CONTROLLER_ID,
        "agent_id": command.get("agent_id"),
        "machine_id": command["machine_id"],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "decision_type": command.get(
            "decision_type",
            "UNKNOWN",
        ),
        "action": command["action"],
        "risk_score": command["risk_score"],
        "recovery_attempt": command.get(
            "recovery_attempt",
            0,
        ),
        **execution_result,
    }


def create_machine_state_event(
    command_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "state_event_id": str(uuid.uuid4()),
        "source_result_id": command_result[
            "result_id"
        ],
        "source_command_id": command_result[
            "command_id"
        ],
        "source_decision_id": command_result[
            "decision_id"
        ],
        "correlation_id": command_result[
            "correlation_id"
        ],
        "controller_id": CONTROLLER_ID,
        "machine_id": command_result[
            "machine_id"
        ],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "speed": command_result[
            "resulting_speed"
        ],
        "previous_speed": command_result[
            "previous_speed"
        ],
        "target_speed": command_result[
            "target_speed"
        ],
        "status": command_result[
            "machine_status"
        ],
        "last_applied_action": command_result[
            "action"
        ],
        "state_changed": command_result[
            "state_changed"
        ],
    }


def delivery_report(
    error,
    message,
) -> None:
    if error is not None:
        print(
            "Errore durante la pubblicazione: "
            f"{error}",
            flush=True,
        )
        return

    print(
        "Evento pubblicato "
        f"topic={message.topic()} "
        f"partition={message.partition()} "
        f"offset={message.offset()}",
        flush=True,
    )


def publish_event(
    producer: Producer,
    topic: str,
    machine_id: str,
    event: dict[str, Any],
) -> None:
    producer.produce(
        topic=topic,
        key=machine_id.encode("utf-8"),
        value=json.dumps(
            event
        ).encode("utf-8"),
        callback=delivery_report,
    )

    producer.poll(0)


def publish_command_result(
    producer: Producer,
    command_result: dict[str, Any],
) -> None:
    publish_event(
        producer=producer,
        topic=COMMAND_RESULTS_TOPIC,
        machine_id=command_result[
            "machine_id"
        ],
        event=command_result,
    )


def publish_machine_state(
    producer: Producer,
    machine_state: dict[str, Any],
) -> None:
    publish_event(
        producer=producer,
        topic=MACHINE_STATE_TOPIC,
        machine_id=machine_state[
            "machine_id"
        ],
        event=machine_state,
    )


def process_command(
    message_value: bytes,
    producer: Producer,
    controller: MachineController,
) -> None:
    command = deserialize_command(
        message_value
    )

    execution_result = (
        controller.execute_command(command)
    )

    command_result = create_command_result(
        command=command,
        execution_result=execution_result,
    )

    publish_command_result(
        producer=producer,
        command_result=command_result,
    )

    machine_state_published = False

    if command_result["result"] == SUCCESS:
        machine_state = create_machine_state_event(
            command_result
        )

        publish_machine_state(
            producer=producer,
            machine_state=machine_state,
        )

        machine_state_published = True

    producer.flush(10)

    print(
        "Comando elaborato "
        f"macchina={command['machine_id']} "
        f"azione={command['action']} "
        f"velocita_precedente="
        f"{execution_result['previous_speed']} "
        f"velocita_obiettivo="
        f"{execution_result['target_speed']} "
        f"velocita_risultante="
        f"{execution_result['resulting_speed']} "
        f"stato_macchina="
        f"{execution_result['machine_status']} "
        f"esecuzione="
        f"{execution_result['execution_number']} "
        f"risultato="
        f"{execution_result['result']} "
        f"machine_state_pubblicato="
        f"{machine_state_published} "
        f"correlation_id="
        f"{command['correlation_id']}",
        flush=True,
    )


def handle_shutdown(
    signum,
    frame,
) -> None:
    del signum, frame

    global running
    running = False

    print(
        "Arresto del Machine Controller richiesto",
        flush=True,
    )


def run_controller() -> None:
    consumer = create_consumer()
    producer = create_producer()

    controller = MachineController(
        mode=CONTROLLER_MODE
    )

    consumer.subscribe(
        [COMMANDS_TOPIC]
    )

    print(
        "Machine Controller avviato: "
        f"{CONTROLLER_ID}",
        flush=True,
    )

    print(
        f"Broker: {KAFKA_BROKER}",
        flush=True,
    )

    print(
        f"Topic comandi: {COMMANDS_TOPIC}",
        flush=True,
    )

    print(
        "Topic risultati: "
        f"{COMMAND_RESULTS_TOPIC}",
        flush=True,
    )

    print(
        "Topic stato macchina: "
        f"{MACHINE_STATE_TOPIC}",
        flush=True,
    )

    print(
        f"Modalita controller: {CONTROLLER_MODE}",
        flush=True,
    )

    try:
        while running:
            message = consumer.poll(
                timeout=1.0
            )

            if message is None:
                continue

            if message.error():
                if (
                    message.error().code()
                    == KafkaError._PARTITION_EOF
                ):
                    continue

                raise KafkaException(
                    message.error()
                )

            try:
                process_command(
                    message_value=message.value(),
                    producer=producer,
                    controller=controller,
                )

                consumer.commit(
                    message=message,
                    asynchronous=False,
                )

            except (
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                print(
                    "Comando non elaborabile "
                    f"topic={message.topic()} "
                    f"partition={message.partition()} "
                    f"offset={message.offset()}: "
                    f"{error}",
                    flush=True,
                )

                consumer.commit(
                    message=message,
                    asynchronous=False,
                )

    finally:
        producer.flush(10)
        consumer.close()

        print(
            "Machine Controller arrestato "
            "correttamente",
            flush=True,
        )


def main() -> None:
    signal.signal(
        signal.SIGINT,
        handle_shutdown,
    )

    signal.signal(
        signal.SIGTERM,
        handle_shutdown,
    )

    run_controller()


if __name__ == "__main__":
    main()