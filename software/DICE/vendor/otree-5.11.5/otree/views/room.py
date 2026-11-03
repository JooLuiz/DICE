import otree.views.cbv

from otree.channels import utils as channel_utils
from otree.room import ROOM_DICT, BaseRoom, _setting_callable
from otree.session import SESSION_CONFIGS_DICT
from otree.templating import render
from otree.views.admin import CreateSessionForm
from .cbv import AdminView


class Rooms(AdminView):
    url_pattern = '/rooms'

    def vars_for_template(self):
        rooms = list(ROOM_DICT.values())
        return {
            'rooms': rooms,
            'room_sessions': [(room, room.get_session()) for room in rooms],
            'dynamic_rooms_enabled': _dynamic_room_callable('DYNAMIC_ROOM_FORM_CONTEXT') is not None,
        }


def _dynamic_room_callable(setting_name):
    """Returns one optional project callback that supplies dynamic-room data or persistence."""
    return _setting_callable(setting_name)


def _room_page_links(request):
    """Returns the admin URLs that room templates cannot reverse on their own."""
    return {'create_room_url': request.url_for('CreateDynamicRoom')}


def _validation_message(error):
    """Returns a dynamic-room validation message, or None when the error is unrelated."""
    if type(error).__name__ != 'DynamicRoomError':
        return None
    return str(error)


class DynamicRooms(AdminView):
    """Renders the dynamic-room index with the shared admin navigation context."""

    url_pattern = '/dynamic_rooms'

    def get(self, request):
        list_context = _dynamic_room_callable('DYNAMIC_ROOM_LIST_CONTEXT')
        if list_context is None:
            return self.redirect('Rooms')
        return self.render_to_response(
            self.get_context_data(**list_context(), **_room_page_links(request))
        )


class CreateDynamicRoom(AdminView):
    """Renders and submits the create-room form through the shared admin context."""

    url_pattern = '/dynamic_rooms/create'

    def get(self, request):
        form_context = _dynamic_room_callable('DYNAMIC_ROOM_FORM_CONTEXT')
        if form_context is None:
            return self.redirect('Rooms')
        selected_session_code = request.query_params.get('session_code', '')
        return self._render_form(form_context(selected_session_code))

    def post(self, request):
        create_room = _dynamic_room_callable('DYNAMIC_ROOM_CREATE')
        form_context = _dynamic_room_callable('DYNAMIC_ROOM_FORM_CONTEXT')
        if create_room is None or form_context is None:
            return self.redirect('Rooms')
        form_data = self.get_post_data()
        session_code = str(form_data.get('session_code') or '')
        try:
            create_room(
                form_data.get('name', ''),
                form_data.get('display_name', ''),
                session_code,
                form_data.get('start_message', ''),
            )
        except ValueError as error:
            message = _validation_message(error)
            if message is None:
                raise
            return self._render_form(
                form_context(
                    session_code,
                    message,
                    form_data.get('name', ''),
                    form_data.get('display_name', ''),
                    form_data.get('start_message', ''),
                )
            )
        return self.redirect('Rooms')

    def _render_form(self, page_data):
        """Merges room-form data into AdminView context before rendering."""
        return self.render_to_response(
            self.get_context_data(**page_data, **_room_page_links(self.request))
        )


class DeleteDynamicRoom(AdminView):
    """Deletes an unassigned dynamic room and re-renders the list when that is invalid."""

    url_pattern = '/dynamic_rooms/{room_name}/delete'

    def post(self, request, room_name):
        delete_room = _dynamic_room_callable('DYNAMIC_ROOM_DELETE')
        list_context = _dynamic_room_callable('DYNAMIC_ROOM_LIST_CONTEXT')
        if delete_room is None or list_context is None:
            return self.redirect('Rooms')
        try:
            delete_room(room_name)
        except ValueError as error:
            message = _validation_message(error)
            if message is None:
                raise
            return render(
                'otree/DynamicRooms.html',
                self.get_context_data(**list_context(message), **_room_page_links(request)),
            )
        return self.redirect('Rooms')


class RoomWithoutSession(AdminView):
    room: BaseRoom
    form_class = CreateSessionForm

    url_pattern = '/room_without_session/{room_name}'

    def intercept_dispatch(self, room_name):
        self.room_name = room_name
        self.room = ROOM_DICT[room_name]
        if self.room.has_session():
            return self.redirect('RoomWithSession', room_name=room_name)

    def get_form(self):
        return CreateSessionForm(data=dict(room_name=self.room_name))

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            configs=SESSION_CONFIGS_DICT.values(),
            participant_urls=self.room.get_participant_urls(self.request),
            room_wide_url=self.room.get_room_wide_url(self.request),
            room=self.room,
            collapse_links=True,
            **kwargs
        )

    def socket_url(self):
        return channel_utils.room_admin_path(self.room.name)


class RoomWithSession(AdminView):
    template_name = 'otree/RoomWithSession.html'
    room = None

    url_pattern = '/room_with_session/{room_name}'

    def intercept_dispatch(self, room_name):
        self.room = ROOM_DICT[room_name]
        if not self.room.has_session():
            return self.redirect('RoomWithoutSession', room_name=room_name)

    def get_context_data(self, **kwargs):
        from otree.asgi import reverse

        session = self.room.get_session()
        session_code = session.code
        return super().get_context_data(
            participant_urls=self.room.get_participant_urls(self.request),
            room_wide_url=self.room.get_room_wide_url(self.request),
            session_url=reverse('SessionMonitor', code=session_code),
            session=session,
            room=self.room,
            collapse_links=True,
            **kwargs
        )


class CloseRoom(AdminView):
    url_pattern = '/CloseRoom/{room_name}'

    def post(self, request, room_name):
        self.room = ROOM_DICT[room_name]
        self.room.set_session(None)
        return self.redirect('RoomWithoutSession', room_name=room_name)
