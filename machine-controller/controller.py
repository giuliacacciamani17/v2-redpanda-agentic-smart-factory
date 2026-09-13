from typing import Any


REDUCE_SPEED = "REDUCE_SPEED"
REQUEST_INSPECTION = "REQUEST_INSPECTION"
EMERGENCY_STOP = "EMERGENCY_STOP"

SUCCESS = "SUCCESS"
FAILED = "FAILED"

MIXED = "MIXED"
ALWAYS_SUCCESS = "ALWAYS_SUCCESS"


class MachineController:
    def __init__(
        self,
        mode: str = MIXED,
    ) -> None:
        self.mode = mode

        self.action_counters: dict[str, int] = {
            REDUCE_SPEED: 0,
            REQUEST_INSPECTION: 0,
            EMERGENCY_STOP: 0,
        }

    def execute_command(
        self,
        command: dict[str, Any],
    ) -> dict[str, Any]:
        action = command["action"]

        current_speed = int(
            command["current_speed"]
        )

        target_speed = int(
            command["target_speed"]
        )

        self._validate_speed_values(
            action=action,
            current_speed=current_speed,
            target_speed=target_speed,
        )

        execution_number = (
            self._next_execution_number(action)
        )

        if self._should_fail(
            action=action,
            execution_number=execution_number,
        ):
            return self._create_failed_result(
                action=action,
                execution_number=execution_number,
                current_speed=current_speed,
                target_speed=target_speed,
            )

        if action == REDUCE_SPEED:
            return self._execute_reduce_speed(
                execution_number=execution_number,
                current_speed=current_speed,
                target_speed=target_speed,
            )

        if action == REQUEST_INSPECTION:
            return self._execute_request_inspection(
                execution_number=execution_number,
                current_speed=current_speed,
                target_speed=target_speed,
            )

        if action == EMERGENCY_STOP:
            return self._execute_emergency_stop(
                execution_number=execution_number,
                current_speed=current_speed,
                target_speed=target_speed,
            )

        return self._create_unsupported_result(
            action=action,
            execution_number=execution_number,
            current_speed=current_speed,
            target_speed=target_speed,
        )

    def _execute_reduce_speed(
        self,
        execution_number: int,
        current_speed: int,
        target_speed: int,
    ) -> dict[str, Any]:
        return self._create_success_result(
            action=REDUCE_SPEED,
            execution_number=execution_number,
            message=(
                "Speed reduction command "
                "executed successfully"
            ),
            previous_speed=current_speed,
            target_speed=target_speed,
            resulting_speed=target_speed,
            machine_status="RUNNING",
        )

    def _execute_request_inspection(
        self,
        execution_number: int,
        current_speed: int,
        target_speed: int,
    ) -> dict[str, Any]:
        return self._create_success_result(
            action=REQUEST_INSPECTION,
            execution_number=execution_number,
            message=(
                "Maintenance inspection request "
                "executed successfully"
            ),
            previous_speed=current_speed,
            target_speed=target_speed,
            resulting_speed=current_speed,
            machine_status="INSPECTION_REQUIRED",
        )

    def _execute_emergency_stop(
        self,
        execution_number: int,
        current_speed: int,
        target_speed: int,
    ) -> dict[str, Any]:
        return self._create_success_result(
            action=EMERGENCY_STOP,
            execution_number=execution_number,
            message=(
                "Emergency stop command "
                "executed successfully"
            ),
            previous_speed=current_speed,
            target_speed=target_speed,
            resulting_speed=0,
            machine_status="STOPPED",
        )

    def _next_execution_number(
        self,
        action: str,
    ) -> int:
        current_value = self.action_counters.get(
            action,
            0,
        )

        execution_number = current_value + 1

        self.action_counters[action] = (
            execution_number
        )

        return execution_number

    def _should_fail(
        self,
        action: str,
        execution_number: int,
    ) -> bool:
        if self.mode == ALWAYS_SUCCESS:
            return False

        if self.mode != MIXED:
            return False

        failure_sequences = {
            REDUCE_SPEED: {1},
            REQUEST_INSPECTION: set(),
            EMERGENCY_STOP: {1},
        }

        failed_executions = failure_sequences.get(
            action,
            set(),
        )

        return (
            execution_number
            in failed_executions
        )

    @staticmethod
    def _validate_speed_values(
        action: str,
        current_speed: int,
        target_speed: int,
    ) -> None:
        if current_speed < 0:
            raise ValueError(
                "La velocita corrente non puo "
                "essere negativa"
            )

        if target_speed < 0:
            raise ValueError(
                "La velocita obiettivo non puo "
                "essere negativa"
            )

        if (
            action == REDUCE_SPEED
            and target_speed >= current_speed
        ):
            raise ValueError(
                "REDUCE_SPEED richiede una velocita "
                "obiettivo inferiore a quella corrente"
            )

        if (
            action == EMERGENCY_STOP
            and target_speed != 0
        ):
            raise ValueError(
                "EMERGENCY_STOP richiede una velocita "
                "obiettivo uguale a zero"
            )

        if (
            action == REQUEST_INSPECTION
            and target_speed != current_speed
):
            raise ValueError(
                "REQUEST_INSPECTION non deve "
                "modificare la velocita"
            )