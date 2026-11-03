"""Explains the fields on the create-session form.

Role: supplies the short text shown under each create-session label and normalizes the
optional session label submitted with that form.
Not in this file: rendering the form, persisting the session, and the sessions list.
Key dependencies: None.
See also: software/DICE/_templates/otree/includes/CreateSessionForm.html,
software/DICE/tests/test_session_field_help.py.
"""

FIELD_HELP = {
    "session_config": "Chooses the platform, shown as Config in the sessions list and room selector.",
    "num_participants": "Sets how many participant slots this session can assign.",
    "label": "Optional admin name shown in the sessions list and at the start of each room option.",
    "language": "Chooses English or Portuguese for fixed participant pages, including the Start button.",
    "completion_redirect_url": "Optional link shown as a button on the final debrief page, such as a Prolific completion link.",
    "step_feed_csv_url": "CSV of posts loaded into the participant feed for this step.",
    "step_survey_link": "External questionnaire opened after this step. Leave blank for in-study questions.",
    "step_questionnaire_json": "Questions shown inside the study after this step. Leave blank for an external survey.",
    "step_questionnaire_title": "Heading on the in-study questionnaire. Blank uses the session-language default.",
    "title": "Researcher's title on the consent form, such as Dr.",
    "full_name": "Researcher's name on the consent form and debrief contact.",
    "eMail": "Contact email on the consent form and debrief page.",
    "study_name": "Participant-facing study name, also shown in the sessions list.",
    "channel_type": "Default feed layout. Each journey step uses this platform.",
    "max_journey_steps": "Maximum number of journey slots this session can contain.",
    "return_param_name": "Query parameter used when an external survey sends the participant back.",
    "bridge_redirect_delay_ms": "Milliseconds the redirect page waits before opening an external survey.",
    "default_return_strategy": "How a participant returns from an external survey when a step does not override it.",
    "dwell_threshold": "Percentage of an item that must be visible before its dwell time counts.",
    "story_duration": "Seconds a story stays on screen before it advances.",
    "url_param": "Participant identifier appended to external survey links.",
    "skip_intro": "Skips the consent page when checked.",
    "skip_briefing": "Skips the briefing page when checked.",
    "briefing": "HTML shown on the briefing page before the first step.",
    "consent_form": "Custom consent HTML. Blank uses the built-in consent text.",
    "survey_link": "Legacy single-step external survey. Journey-step survey links replace it.",
    "data_path": "Legacy single-step feed file. Journey-step CSV links replace it.",
    "delimiter": "Character that separates columns in feed CSV files.",
    "sort_by": "Feed column used to order posts.",
    "condition_col": "Feed column that assigns the participant's condition.",
    "search_term": "Search text shown in feed layouts that include a search box.",
    "topics": "Shows the topic list in feed layouts that support it.",
    "copy_text": "Extra text shown with call-to-action posts.",
    "show_cta": "Shows call-to-action posts when checked.",
    "cta_text": "Button text on call-to-action posts.",
    "participation_fee": "Payment amount stored with the session and shown in session properties.",
    "real_world_currency_per_point": "Currency value of one point, used when points are enabled.",
}

_STEP_HELP_KEYS = {
    "feed_csv_url": "step_feed_csv_url",
    "survey_link": "step_survey_link",
    "questionnaire_json": "step_questionnaire_json",
    "questionnaire_title": "step_questionnaire_title",
}


def help_text(field_name: str) -> str:
    """Returns the explanation for one create-session field.

    Args:
        field_name: Config field name, or a fixed form field such as label.

    Returns:
        The explanation shown below that field's label, or an empty string when unknown.
    """
    normalized_name = str(field_name or "")
    if normalized_name in FIELD_HELP:
        return FIELD_HELP[normalized_name]
    if normalized_name.startswith("step_"):
        for suffix, help_key in _STEP_HELP_KEYS.items():
            if normalized_name.endswith("_" + suffix):
                return FIELD_HELP[help_key]
    return ""


help_text.catalog = FIELD_HELP


def normalize_session_label(value) -> str:
    """Returns the session label stored from the create-session form.

    Args:
        value: Posted label. A one-item list is accepted from form parsers.

    Returns:
        The stripped label. Blank input stays empty.
    """
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value or "").strip()
