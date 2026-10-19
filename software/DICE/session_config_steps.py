"""Builds journey_steps from flat, numbered session-config fields.

This lets a researcher configure a multi-step journey (feed -> questionnaire -> feed ->
questionnaire -> ...) directly on oTree's native "create session" page at /sessions, without
editing settings.py, for any session config (Twitter, Instagram, Stories, Linkedin, Generic).
oTree's session-creation form can only render plain scalar (str/int/float/bool) fields, so each
step is exposed as a fixed, numbered group of fields (step_1_feed_csv_url, step_1_survey_link,
step_1_questionnaire_json, step_2_..., etc.) rather than as a single dynamic list.

Every step in a session shares that session's own channel_type (e.g. a session created from the
"Twitter" config gets Twitter-rendered steps, "Instagram" gets Insta-rendered steps); mixing
channels within a single journey is not supported.

A slot is used when it has a feed CSV, a survey link, or a questionnaire JSON. A slot with
only a questionnaire (or only a survey link) is a questionnaire-only step: the feed page is
skipped for that round. A slot with all three blank is skipped. The resulting raw step dicts
are handed to
DICE/journey_config.py's existing _normalize_step / normalize_questionnaire_questions
pipeline unchanged, so validation and defaults are inherited for free.

This module intentionally lives at the project root (next to settings.py), not inside the
DICE/ app package: settings.py must be able to import MAX_CONFIGURABLE_JOURNEY_STEPS without
triggering DICE/__init__.py (the app's "noself" pages+models module) to execute before oTree
has finished initializing.
"""
import json
from typing import Any, Dict, List


# Number of step slots exposed on the session-creation form. Keep this in sync with the
# step_N_* fields declared in SESSION_CONFIG_DEFAULTS (settings.py) and with the template
# override at _templates/otree/includes/CreateSessionForm.html.
MAX_CONFIGURABLE_JOURNEY_STEPS = 6


def _field(session_config: Dict[str, Any], slot_index: int, suffix: str) -> str:
    return str(session_config.get(f"step_{slot_index}_{suffix}") or "").strip()


def build_steps_from_numbered_fields(session_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reads step_1_feed_csv_url.. step_6_feed_csv_url (and sibling fields) off session_config
    and returns a list of raw journey_steps dicts, one per used slot, in slot order.

    A slot is used when it has a feed CSV, a survey link, or a questionnaire JSON. data_path
    is the feed CSV and may be empty for a questionnaire-only step.
    """
    steps: List[Dict[str, Any]] = []

    for slot_index in range(1, MAX_CONFIGURABLE_JOURNEY_STEPS + 1):
        feed_csv_url = _field(session_config, slot_index, "feed_csv_url")
        survey_link = _field(session_config, slot_index, "survey_link")
        questionnaire_json = _field(session_config, slot_index, "questionnaire_json")
        if not (feed_csv_url or survey_link or questionnaire_json):
            continue  # genuinely unused slot

        step: Dict[str, Any] = {
            "step_id": f"step_{slot_index}",
            "channel_type": session_config.get("channel_type", "Insta"),
            "data_path": feed_csv_url,
            "survey_link": survey_link,
        }

        if questionnaire_json:
            step["questionnaire_questions"] = _parse_questionnaire_json(
                questionnaire_json=questionnaire_json, slot_index=slot_index
            )
            step["questionnaire_mode"] = "internal"

        steps.append(step)

    return steps


def _parse_questionnaire_json(questionnaire_json: str, slot_index: int) -> Any:
    try:
        return json.loads(questionnaire_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"step_{slot_index}_questionnaire_json is not valid JSON: {exc}"
        ) from exc
