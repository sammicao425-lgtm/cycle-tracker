from datetime import date, timedelta, timezone, timedelta as td

import ephem

# Melbourne, Australia
MELBOURNE_LAT = "-37.8136"
MELBOURNE_LON = "144.9631"
MELBOURNE_UTC_OFFSET = 10  # AEST (not accounting for DST, close enough for moon dates)


def _make_observer(d: date) -> ephem.Observer:
    """Create an ephem Observer set to Melbourne for a given date."""
    obs = ephem.Observer()
    obs.lat = MELBOURNE_LAT
    obs.lon = MELBOURNE_LON
    obs.date = ephem.Date(d.strftime("%Y/%m/%d"))
    return obs


def get_moon_info(d: date) -> dict:
    """Return moon phase info for a given date in Melbourne."""
    obs = _make_observer(d)
    moon = ephem.Moon(obs)
    illumination = moon.phase / 100.0

    # Compare with previous day to determine waxing vs waning
    obs_prev = _make_observer(d - timedelta(days=1))
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
    """Return all full and new moon dates in a range, adjusted to Melbourne time."""
    results = []
    d = ephem.Date(start_date.strftime("%Y/%m/%d"))
    end = ephem.Date(end_date.strftime("%Y/%m/%d"))

    # Collect full moons
    cursor = d
    while True:
        fm = ephem.next_full_moon(cursor)
        if fm > end:
            break
        # Convert UTC to Melbourne time (add offset hours)
        fm_melbourne = ephem.Date(fm + MELBOURNE_UTC_OFFSET * ephem.hour)
        fm_date = fm_melbourne.datetime().date()
        results.append({"date": fm_date, "type": "Full Moon"})
        cursor = fm + 1

    # Collect new moons
    cursor = d
    while True:
        nm = ephem.next_new_moon(cursor)
        if nm > end:
            break
        nm_melbourne = ephem.Date(nm + MELBOURNE_UTC_OFFSET * ephem.hour)
        nm_date = nm_melbourne.datetime().date()
        results.append({"date": nm_date, "type": "New Moon"})
        cursor = nm + 1

    results.sort(key=lambda x: x["date"])
    return results
