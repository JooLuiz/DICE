"""Persists and presents administrator-created oTree rooms.

Role: owns dynamic room validation, metadata persistence, native room materialization, and
room/session administration callbacks.
Not in this file: HTTP rendering, CSRF, participant allocation, and the room WebSocket protocol.
Key dependencies: otree.room, otree.models_concrete.RoomToSession, DICE templates.
See also: software/DICE/DICE/room_start_copy.py, software/DICE/tests/test_dynamic_rooms.py.
"""
import time
from typing import Any, Optional

from otree.api import ExtraModel, models
from otree.common import validate_alphanumeric
from otree.database import NoResultFound
from otree.models import Session
from otree.models_concrete import RoomToSession
from otree.room import NoLabelRoom, ROOM_DICT
from sqlalchemy import UniqueConstraint

from DICE.room_start_copy import room_start_presentation  # re-exported as ROOM_START_PRESENTATION

_MAX_START_MESSAGE_LENGTH = 500

class DynamicRoom(ExtraModel):
    """Database record for an administrator-created, unlabeled permanent room."""

    __table_args__ = (UniqueConstraint("name", name="uq_dice_dynamic_room_name"),)

    name = models.StringField()
    display_name = models.StringField()
    start_message = models.StringField(initial="")
    created_at = models.FloatField()
    is_active = models.BooleanField(initial=True)


class DynamicRoomError(ValueError):
    """Raised when a dynamic room request violates a room lifecycle invariant."""

def load_dynamic_room(room_name: str) -> Optional[NoLabelRoom]:
    """Returns the active persisted room for a registry lookup, if one exists.

    Args:
        room_name: Candidate name taken from an oTree room route.

    Returns:
        A native NoLabelRoom for active persisted metadata, or None for an unknown room.
    """
    room_record = _active_room_record(room_name)
    return _materialize_room(room_record) if room_record else None

def list_dynamic_rooms() -> list[NoLabelRoom]:
    """Returns active persisted rooms for native room-index enumeration."""
    return [
        _materialize_room(room_record)
        for room_record in DynamicRoom.objects_filter(is_active=True).order_by(DynamicRoom.name).all()
    ]

def create_dynamic_room(
    name: str,
    display_name: str,
    session: Optional[Session] = None,
    start_message: str = "",
) -> NoLabelRoom:
    """Creates a permanent room and optionally attaches one unassigned session.

    Args:
        name: URL-safe room identifier using letters, numbers, or underscores.
        display_name: Administrator-facing room label.
        session: Existing session to attach. None creates an unassigned room.
        start_message: Confirmation sentence shown before Start. Blank uses the session language.

    Returns:
        The materialized native NoLabelRoom.

    Raises:
        DynamicRoomError: If the name, message, or requested session violates room invariants.

    Side effects:
        Inserts DynamicRoom metadata and may create a native RoomToSession association.
    """
    normalized_name = _validate_room_name(name)
    normalized_display_name = str(display_name or "").strip()
    normalized_start_message = _validate_start_message(start_message)
    if not normalized_display_name:
        raise DynamicRoomError("Display name is required.")
    if _room_record(normalized_name):
        raise DynamicRoomError(f"Room '{normalized_name}' already exists.")
    if dict.__contains__(ROOM_DICT, normalized_name):
        raise DynamicRoomError(f"Room '{normalized_name}' conflicts with a configured static room.")
    if session and _session_room_mapping(session):
        raise DynamicRoomError("The selected session is already attached to a room.")

    room_record = DynamicRoom.create(
        name=normalized_name,
        display_name=normalized_display_name,
        start_message=normalized_start_message,
        created_at=time.time(),
        is_active=True,
    )
    room = _materialize_room(room_record)
    dict.__setitem__(ROOM_DICT, room.name, room)
    if session:
        room.set_session(session)
    return room

def delete_dynamic_room(room_name: str) -> None:
    """Archives an unassigned dynamic room and removes its local registry cache entry.

    Args:
        room_name: Name of the dynamic room to archive.

    Returns:
        None.

    Raises:
        DynamicRoomError: If the room is unknown or still attached to a session.

    Side effects:
        Marks metadata inactive and removes the cached native room object.
    """
    room_record = _require_active_room_record(room_name)
    room = _materialize_room(room_record)
    if room.has_session():
        raise DynamicRoomError("Detach the session before deleting this room.")
    room_record.is_active = False
    ROOM_DICT.discard_dynamic_room(room_record.name)

def create_form_context(
    session_code: str = "",
    error_message: str = "",
    submitted_name: str = "",
    submitted_display_name: str = "",
    submitted_start_message: str = "",
) -> dict[str, Any]:
    """Returns the room-form data an admin view merges into its own template context.

    Args:
        session_code: Session to preselect. Blank leaves the session choice empty.
        error_message: Validation message to show when re-rendering a failed submission.
        submitted_name: Room name to keep after a validation error.
        submitted_display_name: Display name to keep after a validation error.
        submitted_start_message: Confirmation sentence to keep after a validation error.

    Returns:
        Available sessions, the selected session code, active rooms, submitted values, and the error.
    """
    return _admin_context(
        session_code,
        error_message,
        submitted_name,
        submitted_display_name,
        submitted_start_message,
    )

def room_list_context(error_message: str = "") -> dict[str, Any]:
    """Returns the dynamic-room list data for the admin rooms page.

    Args:
        error_message: Deletion failure to display above the list.

    Returns:
        Active room presentations and the error message.
    """
    return _admin_context(error_message=error_message)


def create_room_from_submission(
    name: str,
    display_name: str,
    session_code: str = "",
    start_message: str = "",
) -> NoLabelRoom:
    """Creates a room from admin form values.

    Args:
        name: Requested permanent room name.
        display_name: Administrator-facing label.
        session_code: Existing session to attach. Blank creates an unassigned room.
        start_message: Optional confirmation sentence. Blank uses the session-language default.

    Returns:
        The created native room.

    Raises:
        DynamicRoomError: If the name, display name, message, or selected session is invalid.
    """
    session = None
    normalized_session_code = str(session_code or "")
    if normalized_session_code:
        session = Session.objects_filter(code=normalized_session_code).first()
        if session is None:
            raise DynamicRoomError("The selected session no longer exists.")
    return create_dynamic_room(
        name=name,
        display_name=display_name,
        session=session,
        start_message=start_message,
    )


def room_presentation(room: NoLabelRoom) -> dict[str, str]:
    """Returns the session metadata required by room and session admin templates."""
    session = room.get_session()
    return {
        "name": room.name,
        "display_name": room.display_name,
        "session_code": session.code if session else "",
        "session_config_name": str(session.config.get("name") or "") if session else "",
    }


def session_option_presentation(session: Session) -> dict[str, str]:
    """Returns the human-readable data used by the create-room session selector.

    Args:
        session: Unattached session offered for room association.

    Returns:
        The submitted code and a label containing its optional name, code, and platform.
    """
    config = getattr(session, "config", None) or {}
    platform = str(config.get("name") or "") if isinstance(config, dict) else ""
    label_parts = [str(getattr(session, "label", "") or "").strip(), session.code, platform]
    return {"code": session.code, "option_label": " — ".join(part for part in label_parts if part)}


def _active_room_record(room_name: str) -> Optional[DynamicRoom]:
    try:
        return DynamicRoom.objects_filter(name=room_name, is_active=True).one()
    except NoResultFound:
        return None


def _room_record(room_name: str) -> Optional[DynamicRoom]:
    try:
        return DynamicRoom.objects_filter(name=room_name).one()
    except NoResultFound:
        return None


def _require_active_room_record(room_name: str) -> DynamicRoom:
    room_record = _active_room_record(room_name)
    if room_record is None:
        raise DynamicRoomError("Room does not exist.")
    return room_record


def _materialize_room(room_record: DynamicRoom) -> NoLabelRoom:
    if dict.__contains__(ROOM_DICT, room_record.name):
        room = dict.__getitem__(ROOM_DICT, room_record.name)
    else:
        room = NoLabelRoom(name=room_record.name, display_name=room_record.display_name)
        room.is_dynamic = True
    room.start_message = str(getattr(room_record, "start_message", "") or "")
    return room


def _validate_start_message(start_message: str) -> str:
    normalized_message = str(start_message or "").strip()
    if len(normalized_message) > _MAX_START_MESSAGE_LENGTH:
        raise DynamicRoomError("Confirmation message must be 500 characters or fewer.")
    return normalized_message


def _session_room_mapping(session: Session) -> Optional[RoomToSession]:
    return RoomToSession.objects_filter(session=session).first()


def _validate_room_name(name: str) -> str:
    normalized_name = str(name or "").strip()
    if not normalized_name:
        raise DynamicRoomError("Room name is required.")
    try:
        return validate_alphanumeric(normalized_name, "room name")
    except ValueError as exc:
        raise DynamicRoomError(str(exc)) from exc


def _admin_context(
    selected_session_code: str = "",
    error_message: str = "",
    submitted_name: str = "",
    submitted_display_name: str = "",
    submitted_start_message: str = "",
) -> dict[str, Any]:
    available_sessions = [
        session_option_presentation(session)
        for session in Session.objects_filter().order_by(Session._created).all()
        if _session_room_mapping(session) is None
    ]
    return {
        "rooms": [room_presentation(room) for room in list_dynamic_rooms()],
        "available_sessions": available_sessions,
        "selected_session_code": selected_session_code,
        "error_message": error_message,
        "submitted_name": submitted_name,
        "submitted_display_name": submitted_display_name,
        "submitted_start_message": submitted_start_message,
    }
