"""Unit tests for dynamic room validation and room/session presentation."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from DICE import dynamic_rooms
from otree.room import ROOM_DICT


class DynamicRoomValidationTests(unittest.TestCase):
    def test_room_name_requires_letters_numbers_or_underscores(self):
        # Public room routes must use the same name format as native static rooms.
        self.assertEqual(dynamic_rooms._validate_room_name("forum_study_1"), "forum_study_1")
        with self.assertRaises(dynamic_rooms.DynamicRoomError):
            dynamic_rooms._validate_room_name("forum-study")

    def test_static_room_name_cannot_be_reused(self):
        # A dynamic room must never replace a settings.ROOMS entry in the native registry.
        static_name = "configured_room"
        dict.__setitem__(ROOM_DICT, static_name, SimpleNamespace())
        try:
            with patch.object(dynamic_rooms, "_room_record", return_value=None):
                with self.assertRaises(dynamic_rooms.DynamicRoomError):
                    dynamic_rooms.create_dynamic_room(static_name, "Configured room")
        finally:
            dict.pop(ROOM_DICT, static_name, None)

    def test_create_attaches_the_selected_unassigned_session(self):
        # Creating from session details must use RoomToSession through the native room object.
        session = SimpleNamespace()
        created_record = SimpleNamespace(name="forum_room", display_name="Forum room")
        materialized_room = Mock()

        with (
            patch.object(dynamic_rooms, "_room_record", return_value=None),
            patch.object(dynamic_rooms, "_session_room_mapping", return_value=None),
            patch.object(dynamic_rooms.DynamicRoom, "create", return_value=created_record),
            patch.object(dynamic_rooms, "_materialize_room", return_value=materialized_room),
        ):
            dynamic_rooms.create_dynamic_room("forum_room", "Forum room", session)

        materialized_room.set_session.assert_called_once_with(session)
        dict.pop(ROOM_DICT, "forum_room", None)

    def test_create_stores_the_stripped_confirmation_message(self):
        # Surrounding whitespace is not part of the sentence shown to participants.
        created_record = SimpleNamespace(
            name="forum_room",
            display_name="Forum room",
            start_message="Please begin.",
        )
        with (
            patch.object(dynamic_rooms, "_room_record", return_value=None),
            patch.object(dynamic_rooms, "_session_room_mapping", return_value=None),
            patch.object(dynamic_rooms.DynamicRoom, "create", return_value=created_record) as create_room,
        ):
            room = dynamic_rooms.create_dynamic_room(
                "forum_room",
                "Forum room",
                start_message="  Please begin.  ",
            )

        self.assertEqual(create_room.call_args.kwargs["start_message"], "Please begin.")
        self.assertEqual(room.start_message, "Please begin.")
        dict.pop(ROOM_DICT, "forum_room", None)

    def test_confirmation_message_rejects_more_than_500_characters(self):
        with self.assertRaises(dynamic_rooms.DynamicRoomError):
            dynamic_rooms.create_dynamic_room("forum_room", "Forum room", start_message="x" * 501)

    def test_missing_selected_session_is_rejected_before_persistence(self):
        # A stale session code must not create an unassigned room under another name.
        query = Mock()
        query.first.return_value = None
        with patch.object(dynamic_rooms.Session, "objects_filter", return_value=query):
            with self.assertRaises(dynamic_rooms.DynamicRoomError):
                dynamic_rooms.create_room_from_submission("forum_room", "Forum room", "MISSING")


class DynamicRoomLifecycleTests(unittest.TestCase):
    def test_delete_rejects_a_room_that_still_has_a_session(self):
        # Deleting metadata must not orphan native RoomToSession data.
        record = SimpleNamespace(name="active_room")
        attached_room = Mock()
        attached_room.has_session.return_value = True

        with (
            patch.object(dynamic_rooms, "_require_active_room_record", return_value=record),
            patch.object(dynamic_rooms, "_materialize_room", return_value=attached_room),
        ):
            with self.assertRaises(dynamic_rooms.DynamicRoomError):
                dynamic_rooms.delete_dynamic_room("active_room")

    def test_presentation_reports_the_current_session(self):
        # Both admin surfaces need the same code/config labels for an attached room.
        session = SimpleNamespace(code="SESSION123", config={"name": "Instagram"})
        room = SimpleNamespace(
            name="forum_room",
            display_name="Forum room",
            get_session=lambda: session,
        )
        self.assertEqual(
            dynamic_rooms.room_presentation(room),
            {
                "name": "forum_room",
                "display_name": "Forum room",
                "session_code": "SESSION123",
                "session_config_name": "Instagram",
            },
        )


class SessionOptionPresentationTests(unittest.TestCase):
    def test_labeled_session_includes_name_code_and_platform(self):
        session = SimpleNamespace(
            label="Forum pilot",
            code="ABC123",
            config={"name": "Instagram"},
        )

        self.assertEqual(
            dynamic_rooms.session_option_presentation(session),
            {"code": "ABC123", "option_label": "Forum pilot — ABC123 — Instagram"},
        )

    def test_unlabeled_session_includes_code_and_platform(self):
        session = SimpleNamespace(label=" ", code="XYZ987", config={"name": "Stories"})

        self.assertEqual(
            dynamic_rooms.session_option_presentation(session),
            {"code": "XYZ987", "option_label": "XYZ987 — Stories"},
        )

    def test_admin_context_excludes_attached_sessions_and_returns_presentation_data(self):
        unassigned_session = SimpleNamespace(
            label="Pilot",
            code="OPEN123",
            config={"name": "Twitter"},
        )
        attached_session = SimpleNamespace(
            label="Complete",
            code="USED123",
            config={"name": "Instagram"},
        )
        sessions_query = Mock()
        sessions_query.order_by.return_value.all.return_value = [
            unassigned_session,
            attached_session,
        ]

        with (
            patch.object(dynamic_rooms.Session, "objects_filter", return_value=sessions_query),
            patch.object(
                dynamic_rooms,
                "_session_room_mapping",
                side_effect=lambda session: None if session is unassigned_session else Mock(),
            ),
            patch.object(dynamic_rooms, "list_dynamic_rooms", return_value=[]),
        ):
            context = dynamic_rooms._admin_context()

        self.assertEqual(
            context["available_sessions"],
            [{"code": "OPEN123", "option_label": "Pilot — OPEN123 — Twitter"}],
        )


class RoomStartPresentationTests(unittest.TestCase):
    def test_portuguese_session_uses_the_portuguese_default(self):
        session = SimpleNamespace(config={"language": "pt-br"})
        room = SimpleNamespace(start_message="")
        self.assertEqual(
            dynamic_rooms.room_start_presentation(room, session),
            {
                "start_button_label": "Começar",
                "start_message": "Este estudo começará depois que você confirmar que deseja participar.",
            },
        )

    def test_english_session_uses_the_english_default(self):
        session = SimpleNamespace(config={"language": "en"})
        room = SimpleNamespace()
        self.assertEqual(
            dynamic_rooms.room_start_presentation(room, session)["start_button_label"],
            "Start",
        )
        self.assertIn("confirm that you want to participate", dynamic_rooms.room_start_presentation(room, session)["start_message"])

    def test_saved_message_replaces_the_default_and_keeps_the_session_button(self):
        # A researcher-authored sentence stays as written while the button follows the session.
        session = SimpleNamespace(config={"language": "pt_br"})
        room = SimpleNamespace(start_message="A pesquisa começa quando você confirmar.")
        presentation = dynamic_rooms.room_start_presentation(room, session)
        self.assertEqual(presentation["start_button_label"], "Começar")
        self.assertEqual(presentation["start_message"], "A pesquisa começa quando você confirmar.")


if __name__ == "__main__":
    unittest.main()
