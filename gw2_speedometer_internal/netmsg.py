"""Validation of multiplayer messages received from the network.

Pure functions (no Tk, no sockets) so they can be unit-tested. Messages come
from other players / the server and must be treated as untrusted: a malformed
one must be ignored (and logged), never crash a callback or poison the data
that the HUD later reads on the Tk thread.
"""

import json
import logging

log = logging.getLogger(__name__)

COUNTDOWN_OPTIONS = ("321GO-3", "321GO-2", "321GO-1", "321GO-GO", "321GO-custom")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _to_int(value):
    """int(value) for ints/floats/numeric strings, else None (bools rejected)."""
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def parse_payload(payload):
    """Decode a JSON message payload (bytes or str). Returns a dict or None."""
    try:
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        data = json.loads(payload)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        log.warning("Ignoring malformed network message: %s", exc)
        return None
    if not isinstance(data, dict):
        log.warning("Ignoring network message that is not a JSON object")
        return None
    return data


def validate_race_message(received):
    """Validate/normalise a race message. Returns a dict or None if invalid.

    * "s" (start): needs user, time (number), lap (int-like).
    * "f" / "c" (finish / checkpoint): same plus step (int-like).
    * "321GO-*": no fields required ("321GO-custom" carries a text message).
    Unknown options are returned unchanged for the caller to ignore.
    lap and step are normalised to int, time must be a real number.
    """
    if not isinstance(received, dict):
        return None
    option = received.get("option")
    if not isinstance(option, str):
        return None

    if option in ("s", "f", "c"):
        user = received.get("user")
        time_ = received.get("time")
        lap = _to_int(received.get("lap"))
        if not isinstance(user, str) or not _is_number(time_) or lap is None:
            log.warning("Ignoring invalid '%s' message: %r", option, received)
            return None
        out = {"option": option, "user": user, "time": time_, "lap": lap}
        if option != "s":
            step = _to_int(received.get("step"))
            if step is None:
                log.warning("Ignoring invalid '%s' message (step): %r", option, received)
                return None
            out["step"] = step
        return out

    if option == "321GO-custom":
        message = received.get("message")
        return {"option": option, "message": "" if message is None else str(message)}

    return dict(received)


def parse_countdown_start(payload):
    """For the local websocket: return ``ends_on`` (ms since epoch, number) of a
    valid ``countdown_start`` message, or None for anything else/invalid."""
    data = parse_payload(payload)
    if data is None or data.get("type") != "countdown_start":
        return None
    ends_on = data.get("ends_on")
    if not _is_number(ends_on):
        log.warning("Ignoring countdown_start without numeric ends_on: %r", data)
        return None
    return ends_on
