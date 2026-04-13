from datetime import date, timedelta

import ephem


def get_moon_info(d: date) -> dict:
    """Return moon phase info for a given date."""
    obs = ephem.Observer()
    obs.date = ephem.Date(d.strftime("%Y/%m/%d"))
    moon = ephem.Moon(obs)
    illumination = moon.phase / 100.0  # ephem returns 0-100

    # Compare with previous day to determine waxing vs waning
    obs_prev = ephem.Observer()
    obs_prev.date = ephem.Date((d - timedelta(days=1)).strftime("%Y/%m/%d"))
    moon_prev = ephem.Moon(obs_prev)
    waxing = moon.phase > moon_prev.phase

    if illumination < 0.03:
        name = "New Moon"
    elif illumination > 0.97:
        name = "Full Moon"
    elif waxing and illumination < 0.48:
        name = "Waxing Crescent"
    elif waxing:
        name = "Waxing Gibbous"
    elif not waxing and illumination > 0.52:
        name = "Waning Gibbous"
    else:
        name = "Waning Crescent"

    is_key = name in ("New Moon", "Full Moon")

    return {
        "phase_name": name,
        "illumination": illumination,
        "is_key_phase": is_key,
    }


def get_key_moon_dates(start_date: date, end_date: date) -> list[dict]:
    """Return all full and new moon dates in a range using ephem's precise functions."""
    results = []
    d = ephem.Date(start_date.strftime("%Y/%m/%d"))
    end = ephem.Date(end_date.strftime("%Y/%m/%d"))

    # Collect full moons
    cursor = d
    while True:
        fm = ephem.next_full_moon(cursor)
        if fm > end:
            break
        fm_date = ephem.Date(fm).datetime().date()
        results.append({"date": fm_date, "type": "Full Moon"})
        cursor = fm + 1  # advance past this one

    # Collect new moons
    cursor = d
    while True:
        nm = ephem.next_new_moon(cursor)
        if nm > end:
            break
        nm_date = ephem.Date(nm).datetime().date()
        results.append({"date": nm_date, "type": "New Moon"})
        cursor = nm + 1

    results.sort(key=lambda x: x["date"])
    return results
