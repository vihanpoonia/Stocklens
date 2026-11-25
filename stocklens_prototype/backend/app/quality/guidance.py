def deviation(low: float, high: float, actual: float) -> dict:
    mid = (low + high) / 2
    if actual > high: status = "beat"
    elif actual < low: status = "missed"
    else: status = "met"
    return {"midpoint": mid, "deviation_vs_midpoint": round(actual - mid, 2), "status": status}
