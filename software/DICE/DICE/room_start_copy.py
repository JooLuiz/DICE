"""Chooses the room Start-page sentence and button from the session language.

Role: maps an attached session language and an optional room message to Start-page copy.
Not in this file: room persistence, HTTP rendering, and participant allocation.
Key dependencies: DICE.ui_strings.
See also: software/DICE/DICE/dynamic_rooms.py, software/DICE/tests/test_dynamic_rooms.py.
"""

from DICE.ui_strings import get_ui


def room_start_presentation(room, session) -> dict[str, str]:
    """Returns the Start-page sentence and button for the attached session language.

    Args:
        room: Native room. A dynamic room may carry start_message; a static room does not.
        session: Attached session whose config language selects the catalog.

    Returns:
        start_button_label and start_message. A saved message replaces the locale default.
    """
    config = getattr(session, "config", None) or {}
    language = config.get("language") if isinstance(config, dict) else None
    ui = get_ui(language)
    custom_message = str(getattr(room, "start_message", "") or "").strip()
    return {
        "start_button_label": ui["intro_start"],
        "start_message": custom_message or ui["room_start_message_default"],
    }
