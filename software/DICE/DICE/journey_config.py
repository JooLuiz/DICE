from typing import Any, Dict, List, Optional

from .questionnaire_schema import normalize_questionnaire_questions


JourneyStep = Dict[str, Any]


def _default_legacy_step(session_config: Dict[str, Any]) -> JourneyStep:
    return {
        "step_id": "step_1",
        "channel_type": session_config.get("channel_type", "Twitter"),
        "data_path": session_config.get("data_path", ""),
        "delimiter": session_config.get("delimiter", ";"),
        "condition_col": session_config.get("condition_col", "condition"),
        "survey_link": session_config.get("survey_link", ""),
        "url_param": session_config.get("url_param", "PROLIFIC_PID"),
        "topics": session_config.get("topics", True),
        "show_cta": session_config.get("show_cta", False),
        "search_term": session_config.get("search_term", "@9GAG"),
        "return_strategy": session_config.get("default_return_strategy", "auto_or_manual"),
        "questionnaire_mode": session_config.get("default_questionnaire_mode", "external"),
        "questionnaire_id": session_config.get("questionnaire_id", ""),
        "questionnaire_questions": session_config.get("questionnaire_questions", []),
    }


def _normalize_step(raw_step: Dict[str, Any], step_index: int, session_config: Dict[str, Any]) -> JourneyStep:
    legacy_defaults = _default_legacy_step(session_config)
    normalized_step = dict(legacy_defaults)
    normalized_step.update(raw_step)
    normalized_step["step_id"] = str(normalized_step.get("step_id") or f"step_{step_index + 1}")
    normalized_step["channel_type"] = str(normalized_step.get("channel_type") or legacy_defaults["channel_type"])
    normalized_step["survey_link"] = str(normalized_step.get("survey_link") or "")
    normalized_step["delimiter"] = str(normalized_step.get("delimiter") or legacy_defaults["delimiter"])
    normalized_step["condition_col"] = str(normalized_step.get("condition_col") or legacy_defaults["condition_col"])
    normalized_step["url_param"] = str(normalized_step.get("url_param") or legacy_defaults["url_param"])

    normalized_step["questionnaire_mode"] = str(normalized_step.get("questionnaire_mode") or "external")
    normalized_step["questionnaire_id"] = str(normalized_step.get("questionnaire_id") or "")
    normalized_step["questionnaire_questions"] = normalize_questionnaire_questions(
        raw_questions=normalized_step.get("questionnaire_questions"),
        step_id=normalized_step["step_id"],
    )
    if normalized_step["questionnaire_mode"] == "internal" and not normalized_step["questionnaire_questions"]:
        raise ValueError(
            f"Step '{normalized_step['step_id']}' uses questionnaire_mode='internal' but has no "
            f"'questionnaire_questions' configured."
        )

    return normalized_step


def resolve_journey_steps(session_config: Dict[str, Any], max_supported_steps: int) -> List[JourneyStep]:
    configured_steps = session_config.get("journey_steps") or []
    if not configured_steps:
        configured_steps = [_default_legacy_step(session_config)]

    max_journey_steps = int(session_config.get("max_journey_steps", max_supported_steps))
    effective_step_limit = min(max_journey_steps, max_supported_steps)
    if len(configured_steps) > effective_step_limit:
        raise ValueError(
            f"journey_steps has {len(configured_steps)} steps, but the limit is {effective_step_limit}. "
            f"Increase max_journey_steps or reduce journey_steps."
        )

    return [
        _normalize_step(raw_step=step, step_index=step_index, session_config=session_config)
        for step_index, step in enumerate(configured_steps)
    ]


def get_or_create_journey_steps(session, max_supported_steps: int) -> List[JourneyStep]:
    cached_steps = session.vars.get("journey_steps_resolved")
    if cached_steps:
        return cached_steps
    resolved_steps = resolve_journey_steps(session_config=session.config, max_supported_steps=max_supported_steps)
    session.vars["journey_steps_resolved"] = resolved_steps
    return resolved_steps


def get_step_config_for_round(session, round_number: int, max_supported_steps: int) -> Optional[JourneyStep]:
    journey_steps = get_or_create_journey_steps(session=session, max_supported_steps=max_supported_steps)
    if 1 <= round_number <= len(journey_steps):
        return journey_steps[round_number - 1]
    return None


def get_total_active_rounds(session, max_supported_steps: int) -> int:
    journey_steps = get_or_create_journey_steps(session=session, max_supported_steps=max_supported_steps)
    return len(journey_steps)


def is_active_round(session, round_number: int, max_supported_steps: int) -> bool:
    return round_number <= get_total_active_rounds(session=session, max_supported_steps=max_supported_steps)


def is_last_active_round(session, round_number: int, max_supported_steps: int) -> bool:
    return round_number == get_total_active_rounds(session=session, max_supported_steps=max_supported_steps)
