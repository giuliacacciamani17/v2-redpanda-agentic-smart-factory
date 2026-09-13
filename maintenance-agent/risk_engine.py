from state import MachineState


NORMAL_TEMPERATURE = 65.0
CRITICAL_TEMPERATURE = 90.0

NORMAL_VIBRATION = 2.0
CRITICAL_VIBRATION = 7.0

TEMPERATURE_WEIGHT = 0.45
VIBRATION_WEIGHT = 0.45
TREND_WEIGHT = 0.10


def calculate_risk(state: MachineState) -> float:
    temperature_risk = normalize(
        state.average_temperature(),
        NORMAL_TEMPERATURE,
        CRITICAL_TEMPERATURE,
    )

    vibration_risk = normalize(
        state.average_vibration(),
        NORMAL_VIBRATION,
        CRITICAL_VIBRATION,
    )

    trend_risk = calculate_trend_risk(state)

    total_risk = (
        temperature_risk * TEMPERATURE_WEIGHT
        + vibration_risk * VIBRATION_WEIGHT
        + trend_risk * TREND_WEIGHT
    )

    return round(min(total_risk, 1.0), 2)


def calculate_trend_risk(state: MachineState) -> float:
    if not state.has_enough_history():
        return 0.0

    rising_metrics = sum(
        (
            state.temperature_is_rising(),
            state.vibration_is_rising(),
        )
    )

    return rising_metrics / 2


def normalize(
    value: float,
    normal_value: float,
    critical_value: float,
) -> float:
    if value <= normal_value:
        return 0.0

    if value >= critical_value:
        return 1.0

    return (
        (value - normal_value)
        / (critical_value - normal_value)
    )