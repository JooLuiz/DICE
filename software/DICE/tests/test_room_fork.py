"""Regression tests for DICE's pinned oTree room extension seams."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from DICE.dynamic_rooms import DynamicRoomError
from otree.room import NoLabelRoom, RoomRegistry
from otree.views import participant, room as room_views


class RoomRegistryTests(unittest.TestCase):
    def test_unknown_name_is_loaded_and_cached(self):
        # HTTP and WebSocket membership checks must recognize persisted rooms after a restart.
        loaded_room = NoLabelRoom(name="forum_room", display_name="Forum room")
        registry = RoomRegistry()

        with patch(
            "otree.room._setting_callable",
            return_value=lambda name: loaded_room if name == "forum_room" else None,
        ):
            self.assertIn("forum_room", registry)
            self.assertIs(registry["forum_room"], loaded_room)
            self.assertIs(registry["forum_room"], loaded_room)

    def test_values_merges_persisted_rooms_for_admin_listing(self):
        # The native Rooms view calls values(), so dynamic rooms must appear there too.
        listed_room = NoLabelRoom(name="forum_room", display_name="Forum room")
        registry = RoomRegistry()

        def setting_callable(setting_name):
            if setting_name == "ROOM_REGISTRY_LISTER":
                return lambda: [listed_room]
            return None

        with patch("otree.room._setting_callable", side_effect=setting_callable):
            self.assertEqual(list(registry.values()), [listed_room])


class RoomConfirmationTests(unittest.TestCase):
    def test_get_shows_confirmation_without_allocating_a_participant(self):
        # Forum previews issue GET requests; they must not consume a participant slot.
        room = Mock()
        room.has_participant_labels = False
        room.get_session.return_value = SimpleNamespace()
        request = SimpleNamespace(
            path_params={"room_name": "forum_room"},
            query_params={},
            session={},
        )
        view = object.__new__(participant.AssignVisitorToRoom)

        with (
            patch.dict(participant.ROOM_DICT, {"forum_room": room}, clear=True),
            patch.object(participant, "render", return_value="confirmation") as render_mock,
            patch.object(participant, "participant_or_none_if_exceeded") as allocate_mock,
        ):
            response = view.get(request)

        self.assertEqual(response, "confirmation")
        render_mock.assert_called_once()
        allocate_mock.assert_not_called()

    def test_post_allocates_after_confirmation(self):
        # The explicit Start POST preserves the native participant allocation behavior.
        room = Mock()
        session = SimpleNamespace()
        room.has_participant_labels = False
        room.get_session.return_value = session
        participant_record = SimpleNamespace(_start_url=lambda: "/InitializeParticipant/CODE123")
        request = SimpleNamespace(
            path_params={"room_name": "forum_room"},
            query_params={},
            session={},
        )
        view = object.__new__(participant.AssignVisitorToRoom)

        with (
            patch.dict(participant.ROOM_DICT, {"forum_room": room}, clear=True),
            patch.object(
                participant,
                "participant_or_none_if_exceeded",
                return_value=participant_record,
            ) as allocate_mock,
        ):
            response = view.post(request)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/InitializeParticipant/CODE123")
        allocate_mock.assert_called_once_with(session, label="", cookies=request.session)


class DynamicRoomAdminRenderingTests(unittest.TestCase):
    def _admin_request(self, query_params=None):
        return SimpleNamespace(
            session={},
            query_params=query_params or {},
            url_for=lambda route_name, **kwargs: f"/{route_name}",
        )

    def _page_data(self, session_code="", error_message=""):
        return {
            "available_sessions": [],
            "selected_session_code": session_code,
            "error_message": error_message,
            "rooms": [],
            "submitted_name": "",
            "submitted_display_name": "",
            "submitted_start_message": "",
        }

    def test_create_form_renders_with_admin_view_and_csrf_token(self):
        # BaseAdmin.html reads view and the CSRF token, so both must exist before rendering.
        view = object.__new__(room_views.CreateDynamicRoom)
        view.request = self._admin_request({"session_code": "ABC123"})

        def setting_callable(setting_name):
            if setting_name == "DYNAMIC_ROOM_FORM_CONTEXT":
                return lambda session_code="", error_message="", submitted_name="", submitted_display_name="", submitted_start_message="": self._page_data(session_code, error_message)
            return None

        with patch("otree.views.room._setting_callable", side_effect=setting_callable):
            response = view.get(view.request)

        body = response.body.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Create a persistent room", body)
        self.assertIn('name="csrftoken"', body)

    def test_invalid_submission_rerenders_the_form(self):
        # A domain validation failure stays on the form instead of redirecting to Rooms.
        view = object.__new__(room_views.CreateDynamicRoom)
        view.request = self._admin_request()
        view.get_post_data = lambda: {
            "name": "bad-name",
            "display_name": "",
            "session_code": "ABC123",
        }

        def reject_room(name, display_name, session_code="", start_message=""):
            raise DynamicRoomError("Display name is required.")

        def setting_callable(setting_name):
            if setting_name == "DYNAMIC_ROOM_FORM_CONTEXT":
                return lambda session_code="", error_message="", submitted_name="", submitted_display_name="", submitted_start_message="": self._page_data(session_code, error_message)
            if setting_name == "DYNAMIC_ROOM_CREATE":
                return reject_room
            return None

        with patch("otree.views.room._setting_callable", side_effect=setting_callable):
            response = view.post(view.request)

        body = response.body.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Display name is required.", body)
        self.assertIn('name="csrftoken"', body)


class RoomStartPageTests(unittest.TestCase):
    def test_confirmation_template_shows_the_room_name_once_inside_the_card(self):
        # The page title block used to print the room name again outside the card.
        room = SimpleNamespace(display_name="Forum study", name="forum_room")
        response = participant.render(
            "otree/RoomStartConfirmation.html",
            {
                "room": room,
                "room_name": "forum_room",
                "participant_label": "",
                "secure_hash": "",
                "start_message": "Please begin.",
                "start_button_label": "Começar",
            },
        )

        body = response.body.decode()
        self.assertEqual(body.count("Forum study"), 1)
        self.assertLess(body.find('class="card'), body.find("Forum study"))
        self.assertIn("Começar", body)
        self.assertIn("Please begin.", body)

    def test_attached_session_uses_the_presentation_hook(self):
        # The fork supplies the session; DICE chooses the button and sentence.
        room = Mock()
        room.has_participant_labels = False
        session = SimpleNamespace(config={"language": "pt-br"})
        room.get_session.return_value = session
        request = SimpleNamespace(
            path_params={"room_name": "forum_room"},
            query_params={},
            session={},
        )
        view = object.__new__(participant.AssignVisitorToRoom)

        def presentation(presented_room, presented_session):
            self.assertIs(presented_room, room)
            self.assertIs(presented_session, session)
            return {"start_button_label": "Começar", "start_message": "Mensagem salva."}

        with (
            patch.dict(participant.ROOM_DICT, {"forum_room": room}, clear=True),
            patch.object(participant, "render", return_value="confirmation") as render_mock,
            patch.object(participant, "participant_or_none_if_exceeded") as allocate_mock,
            patch.object(participant, "_setting_callable", return_value=presentation),
        ):
            response = view.get(request)

        self.assertEqual(response, "confirmation")
        allocate_mock.assert_not_called()
        rendered_context = render_mock.call_args.args[1]
        self.assertEqual(rendered_context["start_button_label"], "Começar")
        self.assertEqual(rendered_context["start_message"], "Mensagem salva.")


if __name__ == "__main__":
    unittest.main()
