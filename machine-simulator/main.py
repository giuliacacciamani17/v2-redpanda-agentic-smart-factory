import json
import random
import signal
import time
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
    CORRELATION_PREFIX,
    CORRELATION_START,
    EVENT_INTERVAL_SECONDS,
    KAFKA_BROKER,
    MACHINE_ID,
    MACHINE_STATE_TOPIC,
    RANDOM_SEED,
    STATE_READ_TIMEOUT_SECONDS,
    TELEMETRY_TOPIC,
    validate_configuration,
)

#sequenza standard di degrado progressivo
EVENT_PROFILES = (
    {
        "phase": "NORMAL",
        "temperature": 60.0,
        "vibration": 1.5,
        "speed": 1400,
        "energy_consumption": 95.0,
    },
    {
        "phase": "MONITORING",
        "temperature": 80.0,
        "vibration": 5.5,
        "speed": 1420,
        "energy_consumption": 112.0,
    },
    {
        "phase": "DEGRADING",
        "temperature": 94.0,
        "vibration": 6.9,
        "speed": 1450,
        "energy_consumption": 128.0,
    },
    {
        "phase": "SEVERE",
        "temperature": 100.0,
        "vibration": 9.0,
        "speed": 1470,
        "energy_consumption": 140.0,
    },
    {
        "phase": "CRITICAL",
        "temperature": 105.0,
        "vibration": 10.0,
        "speed": 1500,
        "energy_consumption": 150.0,
    },
)

#sequenza standard di degrado progressivo
STOPPED_PROFILES = (
    {
        "phase": "COOLING",
        "temperature": 82.0,
        "vibration": 0.30,
        "speed": 0,
        "energy_consumption": 18.0,
    },
    {
        "phase": "COOLING",
        "temperature": 75.0,
        "vibration": 0.20,
        "speed": 0,
        "energy_consumption": 14.0,
    },
    {
        "phase": "COOLING",
        "temperature": 68.0,
        "vibration": 0.15,
        "speed": 0,
        "energy_consumption": 11.0,
    },
    {
        "phase": "COOLING",
        "temperature": 62.0,
        "vibration": 0.10,
        "speed": 0,
        "energy_consumption": 9.0,
    },
    {
        "phase": "STOPPED",
        "temperature": 58.0,
        "vibration": 0.05,
        "speed": 0,
        "energy_consumption": 7.0,
    },
)

#comportamento della macchina dopo un comando di riduzione velocità
REDUCED_SPEED_PROFILES = (
    {
        "phase": "RECOVERY",
        "temperature": 84.0,
        "vibration": 5.0,
        "speed_offset": 0,
        "energy_consumption": 108.0,
    },
    {
        "phase": "RECOVERY",
        "temperature": 80.0,
        "vibration": 4.5,
        "speed_offset": -10,
        "energy_consumption": 104.0,
    },
    {
        "phase": "STABILIZING",
        "temperature": 76.0,
        "vibration": 4.0,
        "speed_offset": -20,
        "energy_consumption": 100.0,
    },
    {
        "phase": "STABILIZING",
        "temperature": 72.0,
        "vibration": 3.5,
        "speed_offset": -10,
        "energy_consumption": 97.0,
    },
    {
        "phase": "STABLE",
        "temperature": 68.0,
        "vibration": 3.0,
        "speed_offset": 0,
        "energy_consumption": 94.0,
    },
)

#scenario in cui la macchina necessita di un'ispezione
INSPECTION_PROFILES = (
    {
        "phase": "INSPECTION_PENDING",
        "temperature": 82.0,
        "vibration": 5.2,
        "speed_offset": 0,
        "energy_consumption": 110.0,
    },
    {
        "phase": "INSPECTION_PENDING",
        "temperature": 81.0,
        "vibration": 5.0,
        "speed_offset": 0,
        "energy_consumption": 109.0,
    },
    {
        "phase": "INSPECTION_PENDING",
        "temperature": 80.0,
        "vibration": 4.9,
        "speed_offset": 0,
        "energy_consumption": 108.0,
    },
    {
        "phase": "INSPECTION_PENDING",
        "temperature": 79.0,
        "vibration": 4.8,
        "speed_offset": 0,
        "energy_consumption": 107.0,
    },
    {
        "phase": "INSPECTION_PENDING",
        "temperature": 78.0,
        "vibration": 4.7,
        "speed_offset": 0,
        "energy_consumption": 106.0,
    },
)


running = True


def create_producer() -> Producer:
    configuration = {
        "bootstrap.servers": KAFKA_BROKER,
        "client.id": (
            f"machine-simulator-{MACHINE_ID}"
        ),
    }

    return Producer(configuration)


def create_state_consumer() -> Consumer:
    unique_group_id = (
        f"machine-simulator-state-reader-"
        f"{MACHINE_ID}-{uuid.uuid4()}"
    )

    configuration = {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": unique_group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }

    return Consumer(configuration)


def deserialize_machine_state(
    message_value: bytes,
) -> dict[str, Any]:
    machine_state = json.loads(
        message_value.decode("utf-8")
    )

    if not isinstance(machine_state, dict):
        raise TypeError(
            "Lo stato macchina deve essere "
            "un oggetto JSON"
        )

    required_fields = {
        "state_event_id",
        "machine_id",
        "timestamp",
        "speed",
        "status",
        "last_applied_action",
    }

    missing_fields = (
        required_fields
        - machine_state.keys()
    )

    if missing_fields:
        missing_names = ", ".join(
            sorted(missing_fields)
        )

        raise ValueError(
            "Campi mancanti nello stato macchina: "
            f"{missing_names}"
        )

    machine_state["speed"] = int(
        machine_state["speed"]
    )

    if machine_state["speed"] < 0:
        raise ValueError(
            "La velocita dello stato macchina "
            "non puo essere negativa"
        )

    return machine_state


def read_latest_machine_state(
) -> dict[str, Any] | None:
    consumer = create_state_consumer()

    latest_state: dict[str, Any] | None = None

    consumer.subscribe(
        [MACHINE_STATE_TOPIC]
    )

    deadline = (
        time.monotonic()
        + STATE_READ_TIMEOUT_SECONDS
    )

    print(
        "Ricerca dell'ultimo stato macchina "
        f"topic={MACHINE_STATE_TOPIC} "
        f"machine_id={MACHINE_ID}",
        flush=True,
    )

    try:
        while (
            running
            and time.monotonic() < deadline
        ):
            remaining_time = max(
                deadline - time.monotonic(),
                0.1,
            )

            message = consumer.poll(
                timeout=min(remaining_time, 0.5)
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
                machine_state = (
                    deserialize_machine_state(
                        message.value()
                    )
                )

            except (
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                print(
                    "Stato macchina ignorato "
                    f"partition={message.partition()} "
                    f"offset={message.offset()}: "
                    f"{error}",
                    flush=True,
                )
                continue

            if (
                machine_state["machine_id"]
                != MACHINE_ID
            ):
                continue

            latest_state = select_latest_state(
                current_state=latest_state,
                candidate_state=machine_state,
            )

    finally:
        consumer.close()

    if latest_state is None:
        print(
            "Nessuno stato precedente trovato. "
            "Sara utilizzata la simulazione "
            "progressiva iniziale.",
            flush=True,
        )

        return None

    print(
        "Ultimo stato macchina trovato "
        f"status={latest_state['status']} "
        f"speed={latest_state['speed']} "
        f"last_action="
        f"{latest_state['last_applied_action']} "
        f"correlation_id="
        f"{latest_state['correlation_id']}",
        flush=True,
    )

    return latest_state


def select_latest_state(
    current_state: dict[str, Any] | None,
    candidate_state: dict[str, Any],
) -> dict[str, Any]:
    if current_state is None:
        return candidate_state

    current_timestamp = current_state[
        "timestamp"
    ]

    candidate_timestamp = candidate_state[
        "timestamp"
    ]

    if candidate_timestamp > current_timestamp:
        return candidate_state

    return current_state


def select_event_profiles(
    machine_state: dict[str, Any] | None,
) -> tuple[tuple[dict[str, Any], ...], str]:
    if machine_state is None:
        return (
            EVENT_PROFILES,
            "PROGRESSIVE_DEGRADATION",
        )

    status = machine_state["status"]
    last_action = machine_state[
        "last_applied_action"
    ]

    if (
        status == "STOPPED"
        or last_action == "EMERGENCY_STOP"
    ):
        return (
            STOPPED_PROFILES,
            "STOPPED_COOLING",
        )

    if status == "INSPECTION_REQUIRED":
        return (
            INSPECTION_PROFILES,
            "INSPECTION_PENDING",
        )

    if last_action == "REDUCE_SPEED":
        return (
            REDUCED_SPEED_PROFILES,
            "RECOVERY_AFTER_SPEED_REDUCTION",
        )

    return (
        EVENT_PROFILES,
        "PROGRESSIVE_DEGRADATION",
    )


def resolve_profile_speed(
    profile: dict[str, Any],
    machine_state: dict[str, Any] | None,
) -> int:
    if "speed" in profile:
        return int(profile["speed"])

    if machine_state is None:
        raise ValueError(
            "Lo stato macchina e necessario "
            "per calcolare la velocita"
        )

    base_speed = int(
        machine_state["speed"]
    )

    speed_offset = int(
        profile.get(
            "speed_offset",
            0,
        )
    )

    return max(
        base_speed + speed_offset,
        0,
    )


def generate_measurements(
    profile: dict[str, Any],
    machine_state: dict[str, Any] | None,
    random_generator: random.Random,
) -> dict[str, Any]:
    base_speed = resolve_profile_speed(
        profile=profile,
        machine_state=machine_state,
    )

    status = "RUNNING"

    if machine_state is not None:
        status = machine_state["status"]

    if profile["phase"] in {
        "COOLING",
        "STOPPED",
    }:
        status = "STOPPED"

    return {
        "temperature": round(
            profile["temperature"]
            + random_generator.uniform(
                -0.4,
                0.4,
            ),
            2,
        ),
        "vibration": round(
            max(
                profile["vibration"]
                + random_generator.uniform(
                    -0.08,
                    0.08,
                ),
                0.0,
            ),
            2,
        ),
        "speed": max(
            base_speed
            + random_generator.randint(
                -5,
                5,
            )
            if base_speed > 0
            else 0,
            0,
        ),
        "energy_consumption": round(
            max(
                profile["energy_consumption"]
                + random_generator.uniform(
                    -1.0,
                    1.0,
                ),
                0.0,
            ),
            2,
        ),
        "phase": profile["phase"],
        "status": status,
    }


def create_correlation_id(
    sequence_number: int,
) -> str:
    correlation_number = (
        CORRELATION_START
        + sequence_number
        - 1
    )

    return (
        f"{CORRELATION_PREFIX}-"
        f"{correlation_number}"
    )


def create_telemetry_event(
    measurements: dict[str, Any],
    sequence_number: int,
    simulation_scenario: str,
    source_machine_state: (
        dict[str, Any] | None
    ),
) -> dict[str, Any]:
    source_state_event_id = None
    source_state_correlation_id = None

    if source_machine_state is not None:
        source_state_event_id = (
            source_machine_state[
                "state_event_id"
            ]
        )

        source_state_correlation_id = (
            source_machine_state[
                "correlation_id"
            ]
        )

    return {
        "event_id": str(uuid.uuid4()),
        "correlation_id": create_correlation_id(
            sequence_number
        ),
        "machine_id": MACHINE_ID,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "sequence_number": sequence_number,
        **measurements,
        "simulation_mode": (
            "STATE_AWARE_CONTROLLED_RANDOM"
        ),
        "simulation_scenario": (
            simulation_scenario
        ),
        "source_state_event_id": (
            source_state_event_id
        ),
        "source_state_correlation_id": (
            source_state_correlation_id
        ),
    }


def handle_delivery(
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
    event: dict[str, Any],
) -> None:
    producer.produce(
        topic=TELEMETRY_TOPIC,
        key=event[
            "machine_id"
        ].encode("utf-8"),
        value=json.dumps(
            event
        ).encode("utf-8"),
        callback=handle_delivery,
    )

    producer.poll(0)


def handle_shutdown(
    signum,
    frame,
) -> None:
    del signum, frame

    global running
    running = False

    print(
        "Arresto del simulatore richiesto",
        flush=True,
    )


def run_simulator() -> None:
    validate_configuration()

    producer = create_producer()

    random_generator = random.Random(
        RANDOM_SEED
    )

    machine_state = read_latest_machine_state()

    (
        event_profiles,
        simulation_scenario,
    ) = select_event_profiles(machine_state)

    published_events = 0

    print(
        f"Simulatore avviato per {MACHINE_ID}",
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
        "Topic stato macchina: "
        f"{MACHINE_STATE_TOPIC}",
        flush=True,
    )

    print(
        f"Scenario: {simulation_scenario}",
        flush=True,
    )

    print(
        f"Eventi pianificati: "
        f"{len(event_profiles)}",
        flush=True,
    )

    print(
        f"Seed pseudocasuale: {RANDOM_SEED}",
        flush=True,
    )

    try:
        for sequence_number, profile in enumerate(
            event_profiles,
            start=1,
        ):
            if not running:
                break

            measurements = generate_measurements(
                profile=profile,
                machine_state=machine_state,
                random_generator=random_generator,
            )

            event = create_telemetry_event(
                measurements=measurements,
                sequence_number=sequence_number,
                simulation_scenario=(
                    simulation_scenario
                ),
                source_machine_state=machine_state,
            )

            publish_event(
                producer=producer,
                event=event,
            )

            remaining_messages = producer.flush(
                10
            )

            if remaining_messages != 0:
                raise RuntimeError(
                    "Impossibile confermare la "
                    "pubblicazione dell'evento"
                )

            published_events += 1

            print(
                f"Evento={sequence_number} "
                f"correlation_id="
                f"{event['correlation_id']} "
                f"fase={event['phase']} "
                f"stato={event['status']} "
                f"velocita={event['speed']} "
                f"temperatura="
                f"{event['temperature']} "
                f"vibrazione="
                f"{event['vibration']}",
                flush=True,
            )

            if (
                sequence_number
                < len(event_profiles)
            ):
                time.sleep(
                    EVENT_INTERVAL_SECONDS
                )

    finally:
        producer.flush(10)

        print(
            "Simulazione terminata: "
            f"{published_events} eventi "
            f"pubblicati su "
            f"{len(event_profiles)}",
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

    run_simulator()


if __name__ == "__main__":
    main()