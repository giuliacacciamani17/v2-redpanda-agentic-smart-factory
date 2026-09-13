NO_ACTION = "NO_ACTION"
MONITOR = "MONITOR"
STOPPED_OBSERVATION = "STOPPED_OBSERVATION"
REDUCE_SPEED = "REDUCE_SPEED"
REQUEST_INSPECTION = "REQUEST_INSPECTION"
EMERGENCY_STOP = "EMERGENCY_STOP"

SUCCESS = "SUCCESS"
FAILED = "FAILED"

MANUAL_INTERVENTION_REQUIRED = (
    "MANUAL_INTERVENTION_REQUIRED"
)


def select_action(risk_score: float) -> str:
    if risk_score >= 0.85:
        return EMERGENCY_STOP

    if risk_score >= 0.65:
        return REQUEST_INSPECTION

    if risk_score >= 0.45:
        return REDUCE_SPEED

    if risk_score >= 0.20:
        return MONITOR

    return NO_ACTION


def select_recovery_action(
    failed_action: str,
    recovery_attempt: int,
    max_recovery_attempts: int,
) -> str | None:
    if recovery_attempt > max_recovery_attempts:
        return None

    recovery_actions = {
        REDUCE_SPEED: REQUEST_INSPECTION,
        REQUEST_INSPECTION: EMERGENCY_STOP,
        EMERGENCY_STOP: EMERGENCY_STOP,
    }

    return recovery_actions.get(failed_action)


def requires_command(action: str) -> bool:
    return action in {
        REDUCE_SPEED,
        REQUEST_INSPECTION,
        EMERGENCY_STOP,
    }


def calculate_target_speed(
    action: str,
    current_speed: int,
    reduction_percentage: float,
) -> int:
    if current_speed < 0:
        raise ValueError(
            "La velocita corrente non puo essere negativa"
        )

    if not 0 <= reduction_percentage <= 100:
        raise ValueError(
            "La percentuale di riduzione deve essere "
            "compresa tra 0 e 100"
        )

    if action == EMERGENCY_STOP:
        return 0

    if action == REDUCE_SPEED:
        reduction_factor = (
            1 - reduction_percentage / 100
        )

        target_speed = round(
            current_speed * reduction_factor
        )

        return max(target_speed, 0)

    return current_speed


def explain_action(
    action: str,
    risk_score: float,
) -> str:
    explanations = {
        NO_ACTION: (
            "Operating conditions are within "
            "normal limits"
        ),
        MONITOR: (
            "A weak anomaly requires additional "
            "monitoring"
        ),
        STOPPED_OBSERVATION: (
            "The machine is stopped. Telemetry is "
            "observed without generating new commands"
        ),
        REDUCE_SPEED: (
            "The risk level requires a speed "
            "reduction"
        ),
        REQUEST_INSPECTION: (
            "The risk level requires a maintenance "
            "inspection"
        ),
        EMERGENCY_STOP: (
            "The risk level requires an emergency "
            "stop"
        ),
    }

    if action not in explanations:
        raise ValueError(
            f"Azione non supportata: {action}"
        )

    explanation = explanations[action]

    return (
        f"{explanation}. "
        f"Risk score: {risk_score:.2f}"
    )


def explain_recovery_action(
    failed_action: str,
    recovery_action: str | None,
    recovery_attempt: int,
) -> str:
    if recovery_action is None:
        return (
            "The maximum number of automatic recovery "
            "attempts has been reached. Manual "
            "intervention is required."
        )

    explanations = {
        REDUCE_SPEED: {
            REQUEST_INSPECTION: (
                "The speed reduction failed. "
                "A maintenance inspection is required."
            ),
        },
        REQUEST_INSPECTION: {
            EMERGENCY_STOP: (
                "The maintenance inspection request "
                "failed. An emergency stop is required."
            ),
        },
        EMERGENCY_STOP: {
            EMERGENCY_STOP: (
                "The emergency stop failed. "
                "A new emergency stop will be attempted."
            ),
        },
    }

    action_explanations = explanations.get(
        failed_action,
        {},
    )

    explanation = action_explanations.get(
        recovery_action,
        (
            "The previous action failed. "
            "A recovery action is required."
        ),
    )

    return (
        f"{explanation} "
        f"Recovery attempt: {recovery_attempt}."
    )