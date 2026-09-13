import json
import signal
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Producer,
)

from config import (
    AGENT_FEEDBACK_TOPIC,
    AGENT_ID,
    COMMAND_RESULTS_TOPIC,
    COMMANDS_TOPIC,
    CONSUMER_GROUP,
    DECISIONS_TOPIC,
    KAFKA_BROKER,
    MAX_RECOVERY_ATTEMPTS,
    SPEED_REDUCTION_PERCENTAGE,
    STATE_WINDOW_SIZE,
    TELEMETRY_TOPIC,
)
from policy import (
    FAILED,
    STOPPED_OBSERVATION,
    SUCCESS,
    calculate_target_speed,
    explain_action,
    explain_recovery_action,
    requires_command,
    select_action,
    select_recovery_action,
)
from risk_engine import calculate_risk
from state import MachineState


machine_states: dict[str, MachineState] = {}
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
        "client.id": AGENT_ID,
    }

    return Producer(configuration)


def deserialize_json(
    message_value: bytes,
) -> dict[str, Any]:
    event = json.loads(
        message_value.decode("utf-8")
    )

    if not isinstance(event, dict):
        raise TypeError(
            "Il messaggio deve essere un oggetto JSON"
        )

    return event


def validate_required_fields(
    event: dict[str, Any],
    required_fields: set[str],
) -> None:
    missing_fields = required_fields - event.keys()

    if not missing_fields:
        return

    missing_names = ", ".join(
        sorted(missing_fields)
    )

    raise ValueError(
        f"Campi mancanti: {missing_names}"
    )


def deserialize_telemetry(
    message_value: bytes,
) -> dict[str, Any]:
    telemetry = deserialize_json(message_value)

    required_fields = {
        "event_id",
        "correlation_id",
        "machine_id",
        "timestamp",
        "temperature",
        "vibration",
        "speed",
        "status",
    }

    validate_required_fields(
        event=telemetry,
        required_fields=required_fields,
    )

    return telemetry


def deserialize_command_result(
    message_value: bytes,
) -> dict[str, Any]:
    command_result = deserialize_json(
        message_value
    )

    required_fields = {
        "result_id",
        "command_id",
        "decision_id",
        "correlation_id",
        "machine_id",
        "action",
        "result",
        "risk_score",
    }

    validate_required_fields(
        event=command_result,
        required_fields=required_fields,
    )

    return command_result


def get_machine_state(
    machine_id: str,
) -> MachineState:
    if machine_id not in machine_states:
        machine_states[machine_id] = MachineState(
            machine_id=machine_id,
            window_size=STATE_WINDOW_SIZE,
        )

    return machine_states[machine_id]


def create_initial_decision_event(
    telemetry: dict[str, Any],
    state: MachineState,
    risk_score: float,
    action: str,
) -> dict[str, Any]:
    return {
        "decision_id": str(uuid4()),
        "decision_type": "INITIAL",
        "agent_id": AGENT_ID,
        "source_event_id": telemetry["event_id"],
        "source_result_id": None,
        "parent_decision_id": None,
        "parent_command_id": None,
        "correlation_id": telemetry[
            "correlation_id"
        ],
        "machine_id": telemetry["machine_id"],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "risk_score": risk_score,
        "average_temperature": round(
            state.average_temperature(),
            2,
        ),
        "average_vibration": round(
            state.average_vibration(),
            2,
        ),
        "average_speed": round(
            state.average_speed(),
            2,
        ),
        "current_speed": state.current_speed,
        "temperature_is_rising": (
            state.temperature_is_rising()
        ),
        "vibration_is_rising": (
            state.vibration_is_rising()
        ),
        "previous_action": state.last_action,
        "previous_command_result": (
            state.last_command_result
        ),
        "selected_action": action,
        "recovery_attempt": 0,
        "reason": explain_action(
            action=action,
            risk_score=risk_score,
        ),
    }


def create_recovery_decision_event(
    command_result: dict[str, Any],
    state: MachineState,
    recovery_action: str,
    recovery_attempt: int,
) -> dict[str, Any]:
    current_speed = int(
        command_result.get(
            "resulting_speed",
            state.current_speed,
        )
    )

    return {
        "decision_id": str(uuid4()),
        "decision_type": "RECOVERY",
        "agent_id": AGENT_ID,
        "source_event_id": (
            state.last_source_event_id
        ),
        "source_result_id": command_result[
            "result_id"
        ],
        "parent_decision_id": command_result[
            "decision_id"
        ],
        "parent_command_id": command_result[
            "command_id"
        ],
        "correlation_id": command_result[
            "correlation_id"
        ],
        "machine_id": command_result[
            "machine_id"
        ],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "risk_score": float(
            command_result["risk_score"]
        ),
        "average_temperature": round(
            state.average_temperature(),
            2,
        ),
        "average_vibration": round(
            state.average_vibration(),
            2,
        ),
        "average_speed": round(
            state.average_speed(),
            2,
        ),
        "current_speed": current_speed,
        "temperature_is_rising": (
            state.temperature_is_rising()
        ),
        "vibration_is_rising": (
            state.vibration_is_rising()
        ),
        "previous_action": command_result[
            "action"
        ],
        "previous_command_result": FAILED,
        "selected_action": recovery_action,
        "recovery_attempt": recovery_attempt,
        "reason": explain_recovery_action(
            failed_action=command_result["action"],
            recovery_action=recovery_action,
            recovery_attempt=recovery_attempt,
        ),
    }


def create_command_event(
    decision: dict[str, Any],
    state: MachineState,
) -> dict[str, Any]:
    action = decision["selected_action"]
    current_speed = int(
        decision.get(
            "current_speed",
            state.current_speed,
        )
    )

    target_speed = calculate_target_speed(
        action=action,
        current_speed=current_speed,
        reduction_percentage=(
            SPEED_REDUCTION_PERCENTAGE
        ),
    )

    command_id = str(uuid4())

    command = {
        "command_id": command_id,
        "decision_id": decision["decision_id"],
        "correlation_id": decision[
            "correlation_id"
        ],
        "agent_id": decision["agent_id"],
        "machine_id": decision["machine_id"],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "decision_type": decision[
            "decision_type"
        ],
        "action": action,
        "risk_score": decision["risk_score"],
        "current_speed": current_speed,
        "target_speed": target_speed,
        "recovery_attempt": decision[
            "recovery_attempt"
        ],
        "reason": decision["reason"],
    }

    state.register_pending_command(
        command_id=command_id,
        decision_id=decision["decision_id"],
        action=action,
    )

    return command


def delivery_report(
    error,
    message,
) -> None:
    if error is not None:
        print(
            f"Errore di pubblicazione: {error}",
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
        value=json.dumps(event).encode("utf-8"),
        callback=delivery_report,
    )

    producer.poll(0)


def publish_decision(
    producer: Producer,
    decision: dict[str, Any],
) -> None:
    publish_event(
        producer=producer,
        topic=DECISIONS_TOPIC,
        machine_id=decision["machine_id"],
        event=decision,
    )


def publish_command(
    producer: Producer,
    command: dict[str, Any],
) -> None:
    publish_event(
        producer=producer,
        topic=COMMANDS_TOPIC,
        machine_id=command["machine_id"],
        event=command,
    )

def select_contextual_action(
    telemetry: dict[str, Any],
    risk_score: float,
) -> str:
    machine_status = str(
        telemetry["status"]
    ).upper()

    current_speed = int(
        telemetry["speed"]
    )

    if machine_status == "STOPPED":
        if current_speed != 0:
            raise ValueError(
                "Una macchina con stato STOPPED "
                "deve avere velocita uguale a zero"
            )

        return STOPPED_OBSERVATION

    return select_action(risk_score)
    
def process_telemetry(
    telemetry: dict[str, Any],
    producer: Producer,
) -> None:
    machine_id = telemetry["machine_id"]
    state = get_machine_state(machine_id)

    state.update_telemetry(telemetry)

    risk_score = calculate_risk(state)

    action = select_contextual_action(
        telemetry=telemetry,
        risk_score=risk_score,
    )

    decision = create_initial_decision_event(
        telemetry=telemetry,
        state=state,
        risk_score=risk_score,
        action=action,
    )

    publish_decision(
        producer=producer,
        decision=decision,
    )

    command_published = False

    if (
        requires_command(action)
        and not state.has_pending_command()
    ):
        command = create_command_event(
            decision=decision,
            state=state,
        )

        publish_command(
            producer=producer,
            command=command,
        )

        command_published = True

    elif (
        requires_command(action)
        and state.has_pending_command()
    ):
        print(
            "Comando non pubblicato: "
            "esiste gia un comando in attesa "
            f"command_id={state.pending_command_id}",
            flush=True,
        )

    print(
        "Telemetria elaborata "
        f"correlation_id="
        f"{telemetry['correlation_id']} "
        f"macchina={machine_id} "
        f"rischio={risk_score:.2f} "
        f"velocita={state.current_speed} "
        f"azione_precedente={state.last_action} "
        f"azione_selezionata={action} "
        f"comando_pubblicato={command_published}",
        flush=True,
    )

    state.last_action = action


def determine_recovery_action(
    command_result: dict[str, Any],
    state: MachineState,
) -> tuple[str | None, int]:
    recovery_attempt = (
        state.register_recovery_attempt()
    )

    recovery_action = select_recovery_action(
        failed_action=command_result["action"],
        recovery_attempt=recovery_attempt,
        max_recovery_attempts=(
            MAX_RECOVERY_ATTEMPTS
        ),
    )

    return recovery_action, recovery_attempt


def create_feedback_event(
    command_result: dict[str, Any],
    state: MachineState,
    recovery_action: str | None,
    recovery_attempt: int,
) -> dict[str, Any]:
    command_succeeded = (
        command_result["result"] == SUCCESS
    )

    if command_succeeded:
        feedback_status = "COMPLETED"
        recovery_required = False
        message = (
            "The command was executed successfully "
            "and the agent updated its internal state."
        )
    elif recovery_action is not None:
        feedback_status = "RECOVERY_SCHEDULED"
        recovery_required = True
        message = explain_recovery_action(
            failed_action=command_result["action"],
            recovery_action=recovery_action,
            recovery_attempt=recovery_attempt,
        )
    else:
        feedback_status = (
            "MANUAL_INTERVENTION_REQUIRED"
        )
        recovery_required = False
        message = explain_recovery_action(
            failed_action=command_result["action"],
            recovery_action=None,
            recovery_attempt=recovery_attempt,
        )

    return {
        "feedback_id": str(uuid4()),
        "agent_id": AGENT_ID,
        "result_id": command_result[
            "result_id"
        ],
        "command_id": command_result[
            "command_id"
        ],
        "decision_id": command_result[
            "decision_id"
        ],
        "correlation_id": command_result[
            "correlation_id"
        ],
        "machine_id": command_result[
            "machine_id"
        ],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "action": command_result["action"],
        "command_result": command_result[
            "result"
        ],
        "feedback_status": feedback_status,
        "previous_speed": command_result.get(
            "previous_speed",
            state.current_speed,
        ),
        "target_speed": command_result.get(
            "target_speed",
            state.current_speed,
        ),
        "current_speed": state.current_speed,
        "machine_status": state.machine_status,
        "state_changed": command_result.get(
            "state_changed",
            False,
        ),
        "recovery_required": recovery_required,
        "next_action": recovery_action,
        "recovery_attempt": recovery_attempt,
        "max_recovery_attempts": (
            MAX_RECOVERY_ATTEMPTS
        ),
        "message": message,
    }


def process_failed_command(
    command_result: dict[str, Any],
    state: MachineState,
    producer: Producer,
    recovery_action: str | None,
    recovery_attempt: int,
) -> None:
    if recovery_action is None:
        print(
            "Recupero automatico terminato "
            f"correlation_id="
            f"{command_result['correlation_id']} "
            f"tentativi={recovery_attempt}",
            flush=True,
        )
        return

    recovery_decision = (
        create_recovery_decision_event(
            command_result=command_result,
            state=state,
            recovery_action=recovery_action,
            recovery_attempt=recovery_attempt,
        )
    )

    publish_decision(
        producer=producer,
        decision=recovery_decision,
    )

    recovery_command = create_command_event(
        decision=recovery_decision,
        state=state,
    )

    publish_command(
        producer=producer,
        command=recovery_command,
    )

    state.last_action = recovery_action

    print(
        "Comando di recupero pubblicato "
        f"correlation_id="
        f"{command_result['correlation_id']} "
        f"azione_fallita="
        f"{command_result['action']} "
        f"nuova_azione={recovery_action} "
        f"tentativo={recovery_attempt}",
        flush=True,
    )


def process_command_result(
    command_result: dict[str, Any],
    producer: Producer,
) -> None:
    machine_id = command_result["machine_id"]
    state = get_machine_state(machine_id)

    state.update_command_result(command_result)

    recovery_action: str | None = None
    recovery_attempt = state.recovery_attempts

    if command_result["result"] == SUCCESS:
        state.reset_recovery()
        recovery_attempt = 0

    elif command_result["result"] == FAILED:
        (
            recovery_action,
            recovery_attempt,
        ) = determine_recovery_action(
            command_result=command_result,
            state=state,
        )

    else:
        raise ValueError(
            "Risultato del comando non supportato: "
            f"{command_result['result']}"
        )

    feedback = create_feedback_event(
        command_result=command_result,
        state=state,
        recovery_action=recovery_action,
        recovery_attempt=recovery_attempt,
    )

    publish_event(
        producer=producer,
        topic=AGENT_FEEDBACK_TOPIC,
        machine_id=machine_id,
        event=feedback,
    )

    print(
        "Feedback pubblicato "
        f"correlation_id="
        f"{command_result['correlation_id']} "
        f"macchina={machine_id} "
        f"azione={command_result['action']} "
        f"risultato={command_result['result']} "
        f"prossima_azione={recovery_action}",
        flush=True,
    )

    if command_result["result"] == FAILED:
        process_failed_command(
            command_result=command_result,
            state=state,
            producer=producer,
            recovery_action=recovery_action,
            recovery_attempt=recovery_attempt,
        )


def process_message(
    topic: str,
    message_value: bytes,
    producer: Producer,
) -> None:
    if topic == TELEMETRY_TOPIC:
        telemetry = deserialize_telemetry(
            message_value
        )

        process_telemetry(
            telemetry=telemetry,
            producer=producer,
        )
        return

    if topic == COMMAND_RESULTS_TOPIC:
        command_result = (
            deserialize_command_result(
                message_value
            )
        )

        process_command_result(
            command_result=command_result,
            producer=producer,
        )
        return

    raise ValueError(
        f"Topic non supportato: {topic}"
    )


def handle_shutdown(
    signum,
    frame,
) -> None:
    del signum, frame

    global running
    running = False

    print(
        "Arresto del Maintenance Agent richiesto",
        flush=True,
    )


def run_agent() -> None:
    consumer = create_consumer()
    producer = create_producer()

    consumer.subscribe(
        [
            TELEMETRY_TOPIC,
            COMMAND_RESULTS_TOPIC,
        ]
    )

    print(
        f"Maintenance Agent avviato: {AGENT_ID}",
        flush=True,
    )
    print(
        f"Broker: {KAFKA_BROKER}",
        flush=True,
    )
    print(
        f"Topic telemetria: {TELEMETRY_TOPIC}",
        flush=True,
    )
    print(
        "Topic risultati dei comandi: "
        f"{COMMAND_RESULTS_TOPIC}",
        flush=True,
    )
    print(
        "Tentativi massimi di recupero: "
        f"{MAX_RECOVERY_ATTEMPTS}",
        flush=True,
    )
    print(
        "Percentuale di riduzione velocita: "
        f"{SPEED_REDUCTION_PERCENTAGE}%",
        flush=True,
    )

    try:
        while running:
            message = consumer.poll(timeout=1.0)

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
                process_message(
                    topic=message.topic(),
                    message_value=message.value(),
                    producer=producer,
                )

                producer.flush(10)

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
                    "Evento non valido "
                    f"topic={message.topic()}: "
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
            "Maintenance Agent arrestato "
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

    run_agent()


if __name__ == "__main__":
    main()