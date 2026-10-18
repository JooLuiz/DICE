from otree.api import *

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
    update_prolific_completion_url,
)
from .questionnaire_models import feed_round_export_suffix, questionnaire_response_export_rows
from .pages_questionnaire import E_Questionnaire


doc = """
Mimic social media feeds with DICE.
"""


class C(BaseConstants):
    NAME_IN_URL = "DICE"
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 20

    RULES_TEMPLATE = "DICE/T_Rules.html"
    CONSENT_TEMPLATE = "DICE/T_Consent.html"
    TOPICS_TEMPLATE = "DICE/T_Trending_Topics.html"
    BANNER_TEMPLATE = "DICE/T_Banner_Ads.html"

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

    scroll_sequence = models.LongStringField(doc="tracks the sequence of feed items a participant scrolled through.")
    viewport_data = models.LongStringField(doc="tracks the time feed items were visible in a participants viewport.")
    rowheight_data = models.LongStringField(doc="tracks the time feed items were visible in a participants viewport.")
    likes_data = models.LongStringField(doc="tracks likes.", blank=True)
    replies_data = models.LongStringField(doc="tracks replies.", blank=True)
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
    if step_config is None:
        subsession.FEED = ""
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
        return dict(custom_consent_available=len(player.session.config["briefing"]) > 0)


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


class C_Feed(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player):
        return is_active_round(player.session, player.round_number, C.NUM_ROUNDS)

    @staticmethod
    def get_form_fields(player: Player):
        fields = [
            "likes_data",
            "replies_data",
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
        tweets_df = player.participant.tweets.reset_index(drop=True)
        return dict(
            tweets=tweets_df.to_dict("index"),
            topics=step_config.get("topics", player.session.config["topics"]),
            search_term=step_config.get("search_term", player.session.config["search_term"]),
            label_available=label_available,
        )

    @staticmethod
    def js_vars(player: Player):
        return dict(
            dwell_threshold=player.session.config["dwell_threshold"],
            story_duration=player.session.config["story_duration"],
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.finished = True
        update_prolific_completion_url(player.session)
        if player.id_in_group != 1:
            player.participant.tweets = ""


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
        return dict(
            survey_link=build_survey_link(player=player, step_config=step_config),
            step_id=step_config.get("step_id", ""),
        )

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
            player.round_number,
            player.step_id,
            player.questionnaire_completion_mode,
            player.callback_valid,
        ]
        yield base_row + feed_round_export_suffix()
        for response_row in questionnaire_response_export_rows(player):
            yield base_row + response_row
