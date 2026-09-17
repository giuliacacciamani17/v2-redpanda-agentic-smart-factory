from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MachineState:
    machine_id: str
    window_size: int

    temperatures: deque[float] = field(init=False)
    vibrations: deque[float] = field(init=False)
    speeds: deque[int] = field(init=False)

    last_action: str = "NO_ACTION"
    last_decision_id: str | None = None
    last_command_id: str | None = None
    last_source_event_id: str | None = None
    last_correlation_id: str | None = None
    last_command_result: str | None = None

    current_speed: int = 0
    machine_status: str = "UNKNOWN"

    pending_command_id: str | None = None
    pending_action: str | None = None

    recovery_attempts: int = 0

    def __post_init__(self) -> None:
        self.temperatures = deque(
            maxlen=self.window_size
        )
        self.vibrations = deque(
            maxlen=self.window_size
        )
        self.speeds = deque(
            maxlen=self.window_size
        )

    def update_telemetry(
        self,
        telemetry: dict[str, Any],
    ) -> None:
        temperature = float(
            telemetry["temperature"]
        )
        vibration = float(
            telemetry["vibration"]
        )
        speed = int(
            telemetry["speed"]
        )

        self.temperatures.append(temperature)
        self.vibrations.append(vibration)
        self.speeds.append(speed)

        self.current_speed = speed

        self.machine_status = telemetry.get(
            "status",
            self.machine_status,
        )

        self.last_source_event_id = telemetry[
            "event_id"
        ]

        self.last_correlation_id = telemetry[
            "correlation_id"
        ]

    def register_pending_command(
        self,
        command_id: str,
        decision_id: str,
        action: str,
    ) -> None:
        self.pending_command_id = command_id
        self.pending_action = action
        self.last_command_id = command_id
        self.last_decision_id = decision_id

    def update_command_result(
        self,
        command_result: dict[str, Any],
    ) -> None:
        self.last_command_id = command_result[
            "command_id"
        ]

        self.last_decision_id = command_result[
            "decision_id"
        ]

        self.last_correlation_id = command_result[
            "correlation_id"
        ]

        self.last_command_result = command_result[
            "result"
        ]

        self.machine_status = command_result.get(
            "machine_status",
            self.machine_status,
        )

        resulting_speed = command_result.get(
            "resulting_speed"
        )

        if resulting_speed is not None:
            self.current_speed = int(
                resulting_speed
            )

        self.pending_command_id = None
        self.pending_action = None

    def register_recovery_attempt(self) -> int:
        self.recovery_attempts += 1
        return self.recovery_attempts

    def reset_recovery(self) -> None:
        self.recovery_attempts = 0

    def average_temperature(self) -> float:
        return self._average(
            self.temperatures
        )

    def average_vibration(self) -> float:
        return self._average(
            self.vibrations
        )

    def average_speed(self) -> float:
        return self._average(
            self.speeds
        )

    def temperature_is_rising(self) -> bool:
        return self._is_rising(
            self.temperatures
        )

    def vibration_is_rising(self) -> bool:
        return self._is_rising(
            self.vibrations
        )

    def has_enough_history(self) -> bool:
        return len(self.temperatures) >= 3

    def has_pending_command(self) -> bool:
        return self.pending_command_id is not None

    @staticmethod
    def _average(
        values: deque,
    ) -> float:
        if not values:
            return 0.0

        return sum(values) / len(values)

    @staticmethod
    def _is_rising(
        values: deque,
    ) -> bool:
        if len(values) < 3:
            return False

        recent_values = list(values)[-3:]

        return (
            recent_values[0]
            < recent_values[1]
            < recent_values[2]
        )