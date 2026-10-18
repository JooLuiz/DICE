import secrets
from typing import Dict, Iterable, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


CALLBACK_FLAG_PARAM = "journey_cb"
CALLBACK_STEP_PARAM = "journey_step_id"
CALLBACK_TOKEN_PARAM = "journey_token"


def append_query_parameters(base_url: str, query_parameters: Iterable[Tuple[str, str]]) -> str:
    url_parts = urlsplit(base_url)
    existing_parameters = dict(parse_qsl(url_parts.query, keep_blank_values=True))
    for parameter_name, parameter_value in query_parameters:
        existing_parameters[parameter_name] = parameter_value
    updated_query = urlencode(existing_parameters, doseq=False)
    return urlunsplit((url_parts.scheme, url_parts.netloc, url_parts.path, updated_query, url_parts.fragment))


def participant_identifier(player) -> str:
    if player.participant.label:
        return player.participant.label
    return player.participant.code


def get_or_create_step_token(player, step_id: str) -> str:
    # Use `.vars.get(...)` rather than attribute access: PARTICIPANT_FIELDS
    # descriptors raise KeyError on first access instead of returning a default.
    step_tokens = player.participant.vars.get("journey_step_tokens") or {}
    if step_id not in step_tokens:
        step_tokens[step_id] = secrets.token_urlsafe(20)
        player.participant.journey_step_tokens = step_tokens
    return step_tokens[step_id]


def build_survey_link(player, step_config: Dict[str, str]) -> str:
    base_survey_link = str(step_config.get("survey_link") or "").strip()
    if not base_survey_link:
        return ""

    step_id = str(step_config.get("step_id") or f"step_{player.round_number}")
    url_param = str(step_config.get("url_param") or player.session.config.get("url_param", "PROLIFIC_PID"))
    survey_parameters = [
        (url_param, participant_identifier(player)),
        ("step_id", step_id),
        ("round_number", str(player.round_number)),
        (CALLBACK_STEP_PARAM, step_id),
        (CALLBACK_TOKEN_PARAM, get_or_create_step_token(player=player, step_id=step_id)),
    ]

    completion_code = player.session.vars.get("completion_code")
    if completion_code:
        survey_parameters.append(("cc", str(completion_code)))
    if player.feed_condition:
        survey_parameters.append(("condition", player.feed_condition))

    return append_query_parameters(base_url=base_survey_link, query_parameters=survey_parameters)


def bridge_js_vars(player, step_config: Dict[str, str]) -> Dict[str, str]:
    step_id = str(step_config.get("step_id") or f"step_{player.round_number}")
    return {
        "survey_link": build_survey_link(player=player, step_config=step_config),
        "return_param_name": player.session.config.get("return_param_name", "return_url"),
        "callback_flag_param": CALLBACK_FLAG_PARAM,
        "callback_step_param": CALLBACK_STEP_PARAM,
        "callback_token_param": CALLBACK_TOKEN_PARAM,
        "callback_step_id": step_id,
        "callback_token": get_or_create_step_token(player=player, step_id=step_id),
        "launch_delay_ms": int(player.session.config.get("bridge_redirect_delay_ms", 1200)),
    }


def callback_is_valid(player, expected_step_id: str, callback_step_id: str, callback_token: str) -> bool:
    step_tokens = player.participant.vars.get("journey_step_tokens") or {}
    expected_token = step_tokens.get(expected_step_id)
    if not expected_token:
        return False
    return callback_step_id == expected_step_id and callback_token == expected_token


def mark_step_completion(player, step_id: str, completion_mode: str, callback_valid: bool) -> None:
    completion_registry = player.participant.vars.get("journey_completed_steps") or {}
    completion_registry[step_id] = {
        "round_number": player.round_number,
        "completion_mode": completion_mode,
        "callback_valid": callback_valid,
    }
    player.participant.journey_completed_steps = completion_registry
    player.participant.journey_current_step = step_id


def update_prolific_completion_url(session) -> None:
    completion_code = session.vars.get("completion_code")
    if completion_code:
        session.vars["prolific_completion_url"] = (
            f"https://app.prolific.com/submissions/complete?cc={completion_code}"
        )
        return

    current_completion_url = session.vars.get("prolific_completion_url")
    if current_completion_url is None:
        session.vars["prolific_completion_url"] = "NA"
        return
    session.vars["prolific_completion_url"] = "https://app.prolific.com/submissions/complete"
