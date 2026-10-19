import json

from otree.api import *

import wide_export_columns  # noqa: F401  installs the wide-CSV step column order on import

from .feed_data import prepare_feed_for_round
from .journey_config import (
    get_or_create_journey_steps,
    get_step_config_for_round,
    is_active_round,
    is_last_active_round,
)
from .questionnaire_bridge import (
    bridge_js_vars,
    build_survey_link,
    callback_is_valid,
    mark_step_completion,
)
from .questionnaire_models import feed_round_export_suffix, questionnaire_response_export_rows
from .pages_questionnaire import E_Questionnaire
from .ui_strings import (
    get_consent_default_template,
    get_debrief_context,
    get_js_strings,
    get_template_context,
    resolve_participant_display_id,
)


doc = """
Mimic social media feeds with DICE.
"""


class C(BaseConstants):
    NAME_IN_URL = "DICE"
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 6  # matches MAX_CONFIGURABLE_JOURNEY_STEPS (session_config_steps.py), the
                    # form's actual step-slot limit

    RULES_TEMPLATE = "DICE/T_Rules.html"
    CONSENT_TEMPLATE = "DICE/T_Consent.html"
    TOPICS_TEMPLATE = "DICE/T_Trending_Topics.html"
    BANNER_TEMPLATE = "DICE/T_Banner_Ads.html"
    FEED_END_TEMPLATE = "DICE/T_Partial_Feed_End.html"
    FEED_END_STORIES_TEMPLATE = "DICE/T_Partial_Feed_End_Stories.html"
    TWITTER_SIDEBAR_TEMPLATE = "DICE/T_Partial_Twitter_Sidebar.html"

    ITEM_TWITTER = "DICE/T_Item_Twitter.html"
    ITEM_LINKEDIN = "DICE/T_Item_Linkedin.html"
    ITEM_MASS_MEDIA = "DICE/T_Item_Mass_Media.html"
    ITEM_GENERIC = "DICE/T_Item_Generic.html"
    ITEM_INSTA = "DICE/T_Item_Insta.html"
    ITEM_STORIES = "DICE/T_Item_Stories.html"


class Subsession(BaseSubsession):
    feed_conditions = models.StringField(doc="indicates the feed condition a player is randomly assigned to")
    FEED = models.StringField(doc="")


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    feed_condition = models.StringField(doc="indicates the feed condition a player is randomly assigned to")
    sequence = models.StringField(doc="prints the sequence of tweets based on doc_id")
    step_id = models.StringField(doc="configured journey step id", blank=True)
    participant_code_display = models.StringField(
        doc="participant label if set, else oTree code; shown as the row identity on the Data tab.",
        blank=True,
    )

    scroll_sequence = models.LongStringField(doc="tracks the sequence of feed items a participant scrolled through.")
    viewport_data = models.LongStringField(doc="tracks the time feed items were visible in a participants viewport.")
    rowheight_data = models.LongStringField(doc="tracks the time feed items were visible in a participants viewport.")
    likes_data = models.LongStringField(doc="tracks likes.", blank=True)
    replies_data = models.LongStringField(doc="tracks replies.", blank=True)
    # New sessions require `otree resetdb` after adding this field.
    reposts_data = models.LongStringField(doc="tracks reposts.", blank=True)
    promoted_post_clicks = models.LongStringField(doc="tracks the clicks on sponsored posts.", blank=True)

    touch_capability = models.BooleanField(
        doc="indicates whether a participant uses a touch device to access survey.",
        blank=True,
    )
    device_type = models.StringField(
        doc="indicates the participant's device type based on screen width.",
        blank=True,
    )
    screen_resolution = models.StringField(
        doc="indicates the participant's screen resolution, i.e., width x height.",
        blank=True,
    )

    questionnaire_completion_mode = models.StringField(doc="auto callback vs manual questionnaire completion", blank=True)
    callback_step_id = models.StringField(doc="callback step id returned by survey platform", blank=True)
    callback_token = models.StringField(doc="callback token returned by survey platform", blank=True)
    callback_received = models.StringField(doc="flag indicating whether callback parameters were returned", blank=True)
    callback_valid = models.BooleanField(doc="callback token validation result", blank=True)

    questionnaire_answers_json = models.LongStringField(
        doc="JSON-encoded answers submitted on the in-system questionnaire page (E_Questionnaire).",
        blank=True,
    )

    feed_items_json = models.LongStringField(
        blank=True,
        doc="JSON-encoded feed items for this round, keyed by display order; replaces the "
        "Participant-level `tweets` field, which incorrectly shared one value across all "
        "rounds of a session (New sessions require `otree resetdb` after adding this field.)",
    )


def _step_config(player: Player):
    return get_step_config_for_round(
        session=player.session,
        round_number=player.round_number,
        max_supported_steps=C.NUM_ROUNDS,
    )


# FUNCTIONS -----
def creating_session(subsession: Subsession):
    get_or_create_journey_steps(session=subsession.session, max_supported_steps=C.NUM_ROUNDS)
    step_config = get_step_config_for_round(
        session=subsession.session,
        round_number=subsession.round_number,
        max_supported_steps=C.NUM_ROUNDS,
    )
    if step_config is None or not step_config.get("data_path"):
        subsession.FEED = ""
        # step_id is otherwise only written inside prepare_feed_for_round. Questionnaire-only
        # steps never call that, but the export still filters responses by player.step_id.
        if step_config is not None:
            for player in subsession.get_players():
                player.step_id = step_config["step_id"]
        return
    prepare_feed_for_round(subsession=subsession, step_config=step_config)


# PAGES
class A_Intro(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player):
        return (
            player.round_number == 1
            and is_active_round(player.session, player.round_number, C.NUM_ROUNDS)
            and not player.session.config["skip_intro"]
        )

    @staticmethod
    def vars_for_template(player: Player):
        language = player.session.config.get("language", "en")
        context = get_template_context(
            language,
            player.participant.code,
            player.participant.label,
        )
        context["custom_consent_available"] = len(player.session.config["consent_form"]) > 0
        context["consent_default_template"] = get_consent_default_template(language)
        return context


class B_Briefing(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player):
        return (
            player.round_number == 1
            and is_active_round(player.session, player.round_number, C.NUM_ROUNDS)
            and not player.session.config["skip_briefing"]
            and len(player.session.config["briefing"]) > 0
        )

    @staticmethod
    def vars_for_template(player: Player):
        return get_template_context(player.session.config.get("language", "en"))


class C_Feed(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player):
        if not is_active_round(player.session, player.round_number, C.NUM_ROUNDS):
            return False
        step_config = _step_config(player) or {}
        return bool(step_config.get("data_path"))

    @staticmethod
    def get_form_fields(player: Player):
        fields = [
            "likes_data",
            "replies_data",
            "reposts_data",
            "promoted_post_clicks",
            "touch_capability",
            "device_type",
            "screen_resolution",
        ]

        step_config = _step_config(player) or {}
        topics = step_config.get("topics", player.session.config["topics"])
        show_cta = step_config.get("show_cta", player.session.config["show_cta"])
        if not (topics and show_cta):
            more_fields = ["scroll_sequence", "viewport_data", "rowheight_data"]
        else:
            more_fields = ["scroll_sequence", "viewport_data", "rowheight_data"]
        return fields + more_fields

    @staticmethod
    def vars_for_template(player: Player):
        label_available = player.participant.label is not None
        step_config = _step_config(player) or {}

        language = player.session.config.get("language", "en")
        context = get_template_context(
            language,
            player.participant.code,
            player.participant.label,
        )
        channel_type = step_config.get("channel_type", player.session.config["channel_type"])
        if channel_type == "Linkedin":
            context["feed_end_seen_text"] = context["ui"]["feed_seen_posts_short"]
        elif channel_type == "Generic":
            context["feed_end_submit_id"] = "submitButton"
        context.update(
            tweets=json.loads(player.feed_items_json),
            topics=step_config.get("topics", player.session.config["topics"]),
            search_term=step_config.get("search_term", player.session.config["search_term"]),
            label_available=label_available,
        )
        return context

    @staticmethod
    def js_vars(player: Player):
        language = player.session.config.get("language", "en")
        return dict(
            dwell_threshold=player.session.config["dwell_threshold"],
            story_duration=player.session.config["story_duration"],
            **get_js_strings(language),
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.finished = True
        player.participant_code_display = resolve_participant_display_id(
            player.participant.code, player.participant.label
        )


class D_Redirect(Page):
    form_model = "player"
    form_fields = ["questionnaire_completion_mode", "callback_step_id", "callback_token", "callback_received"]

    @staticmethod
    def is_displayed(player):
        if not is_active_round(player.session, player.round_number, C.NUM_ROUNDS):
            return False
        step_config = _step_config(player) or {}
        if step_config.get("questionnaire_mode", "external") != "external":
            return False
        return len(step_config.get("survey_link", "")) > 0

    @staticmethod
    def vars_for_template(player: Player):
        step_config = _step_config(player) or {}
        context = get_template_context(player.session.config.get("language", "en"))
        context.update(
            survey_link=build_survey_link(player=player, step_config=step_config),
            step_id=step_config.get("step_id", ""),
        )
        return context

    @staticmethod
    def js_vars(player):
        step_config = _step_config(player) or {}
        return bridge_js_vars(player=player, step_config=step_config)

    @staticmethod
    def before_next_page(player, timeout_happened):
        step_config = _step_config(player) or {}
        step_id = step_config.get("step_id", "")

        callback_received = player.callback_received == "1"
        callback_valid = False
        completion_mode = player.questionnaire_completion_mode or "manual_fallback"

        if callback_received:
            callback_valid = callback_is_valid(
                player=player,
                expected_step_id=step_id,
                callback_step_id=player.callback_step_id,
                callback_token=player.callback_token,
            )
            if callback_valid:
                completion_mode = "auto_callback"
            elif completion_mode != "manual_fallback":
                completion_mode = "manual_fallback"

        player.callback_valid = callback_valid
        player.questionnaire_completion_mode = completion_mode
        mark_step_completion(
            player=player,
            step_id=step_id,
            completion_mode=completion_mode,
            callback_valid=callback_valid,
        )


class D_Debrief(Page):
    @staticmethod
    def is_displayed(player):
        return (
            is_active_round(player.session, player.round_number, C.NUM_ROUNDS)
            and is_last_active_round(player.session, player.round_number, C.NUM_ROUNDS)
        )

    @staticmethod
    def vars_for_template(player: Player):
        return get_debrief_context(player)


page_sequence = [A_Intro, B_Briefing, C_Feed, D_Redirect, E_Questionnaire, D_Debrief]


def custom_export(players):
    yield [
        "session",
        "participant_code",
        "participant_label",
        "participant_in_session",
        "condition",
        "item_sequence",
        "scroll_sequence",
        "item_dwell_time",
        "likes",
        "replies",
        "reposts",
        "promoted_clicks",
        "round_number",
        "step_id",
        "questionnaire_completion_mode",
        "callback_valid",
        "record_type",
        "question_id",
        "question_prompt",
        "question_type",
        "answer_value",
    ]

    for player in players:
        participant = player.participant
        session = player.session
        if not is_active_round(session, player.round_number, C.NUM_ROUNDS):
            continue

        base_row = [
            session.code,
            participant.code,
            participant.label,
            player.id_in_group,
            player.feed_condition,
            player.sequence,
            player.scroll_sequence,
            player.viewport_data,
            player.likes_data,
            player.replies_data,
            player.reposts_data,
            player.promoted_post_clicks,
            player.round_number,
            player.step_id,
            player.questionnaire_completion_mode,
            player.callback_valid,
        ]
        yield base_row + feed_round_export_suffix()
        for response_row in questionnaire_response_export_rows(player):
            yield base_row + response_row
