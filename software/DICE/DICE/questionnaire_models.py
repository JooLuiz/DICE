"""Storage and retrieval for answers submitted on in-system (non-external) questionnaire steps.

QuestionnaireResponse is an oTree ExtraModel: a DB table independent of the Player table, keyed
by participant_code/step_id rather than a Player foreign key. This keeps the number of stored
rows free to vary per questionnaire (one row per question) without any schema change, and keeps
responses queryable without joining through oTree's round-based Player bookkeeping.
"""
import json
from typing import Any, Dict, List

from otree.api import ExtraModel, models


class QuestionnaireResponse(ExtraModel):
    session_code = models.StringField()
    participant_code = models.StringField()
    step_id = models.StringField()
    questionnaire_id = models.StringField()
    question_id = models.StringField()
    question_prompt = models.LongStringField()
    question_type = models.StringField()
    answer_value = models.LongStringField(blank=True)


# Trailing export columns appended to every custom_export row; see __init__.py's custom_export.
QUESTIONNAIRE_EXPORT_FIELDS = ["record_type", "question_id", "question_prompt", "question_type", "answer_value"]


def feed_round_export_suffix() -> List[str]:
    """Trailing columns for a plain feed-round export row (no questionnaire response attached)."""
    return ["feed_round", "", "", "", ""]


def save_questionnaire_responses(player, step_config: Dict[str, Any]) -> None:
    """Persists one QuestionnaireResponse row per configured question for this step.

    Called from E_Questionnaire.before_next_page, after oTree has already copied the submitted
    `questionnaire_answers_json` hidden field onto the player.
    """
    questions: List[Dict[str, Any]] = step_config.get("questionnaire_questions") or []
    if not questions:
        return

    submitted_answers = _parse_submitted_answers(player.field_maybe_none("questionnaire_answers_json"))
    questionnaire_id = str(step_config.get("questionnaire_id") or "")
    step_id = str(step_config.get("step_id") or "")

    for question in questions:
        question_id = question["question_id"]
        raw_answer = submitted_answers.get(question_id, "")
        answer_value = json.dumps(raw_answer) if isinstance(raw_answer, list) else str(raw_answer)

        QuestionnaireResponse.create(
            session_code=player.session.code,
            participant_code=player.participant.code,
            step_id=step_id,
            questionnaire_id=questionnaire_id,
            question_id=question_id,
            question_prompt=question["prompt"],
            question_type=question["question_type"],
            answer_value=answer_value,
        )


def questionnaire_response_export_rows(player) -> List[List[str]]:
    """One trailing-column row per answered question, for appending onto a custom_export row."""
    responses = (
        QuestionnaireResponse.objects_filter(
            participant_code=player.participant.code,
            step_id=player.step_id,
        )
        .order_by(QuestionnaireResponse.id)
        .all()
    )
    return [
        ["questionnaire_response", response.question_id, response.question_prompt, response.question_type, response.answer_value]
        for response in responses
    ]


def _parse_submitted_answers(raw_json: str) -> Dict[str, Any]:
    if not raw_json:
        return {}
    try:
        parsed = json.loads(raw_json)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
