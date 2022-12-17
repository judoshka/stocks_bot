def value_to_type(value: int):
    if value < 0.2:
        return 'beginner'
    if value < 0.5:
        return 'middle'
    if value < 0.8:
        return 'trader'
    return 'experienced'


def risk_to_index(risk_value: float) -> int:
    if risk_value > 0.7:
        index = 43
    elif risk_value > 0.5:
        index = 43 * 7
    elif risk_value > 0.2:
        index = 43 * 30
    else:
        index = 43 * 180
    return index


def history_to_risk(object) -> float:
    pass


