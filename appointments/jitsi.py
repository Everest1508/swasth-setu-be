"""Generate public Jitsi Meet room URLs for video appointments."""

import secrets
import string


def create_jitsi_meeting_link() -> str:
    """Return a unique https://meet.jit.si/... URL (no server-side Jitsi account required)."""
    alphabet = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"https://meet.jit.si/room-{suffix}"
