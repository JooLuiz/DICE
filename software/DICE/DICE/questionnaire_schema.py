"""Validation and normalization for in-system (non-external) questionnaire questions.

Question definitions live directly in `journey_steps` config (settings.py), the same way
feed content lives in a CSV path today: no database authoring UI is required to use this
feature, it is purely opt-in per step via `questionnaire_mode="internal"`.
"""
from typing import Any, Dict, List, Optional


QUESTION_TYPE_SINGLE_CHOICE = "single_choice"
QUESTION_TYPE_MULTIPLE_CHOICE = "multiple_choice"
QUESTION_TYPE_LIKERT = "likert"
QUESTION_TYPE_OPEN_TEXT = "open_text"

VALID_QUESTION_TYPES = (
    QUESTION_TYPE_SINGLE_CHOICE,
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_LIKERT,
    QUESTION_TYPE_OPEN_TEXT,
)

CHOICE_QUESTION_TYPES = (QUESTION_TYPE_SINGLE_CHOICE, QUESTION_TYPE_MULTIPLE_CHOICE)


def _normalize_options(raw_options: Optional[List[Dict[str, Any]]], step_id: str, question_id: str) -> List[Dict[str, str]]:
    normalized_options = []
    for raw_option in raw_options or []:
        value = str(raw_option.get("value", "")).strip()
        if not value:
            raise ValueError(
                f"Question '{question_id}' in step '{step_id}' has an option with an empty 'value'."
            )
        label = str(raw_option.get("label") or value)
        normalized_options.append({"value": value, "label": label})
    return normalized_options


def _normalize_likert_options(likert_min: int, likert_max: int) -> List[Dict[str, str]]:
    return [{"value": str(point), "label": str(point)} for point in range(likert_min, likert_max + 1)]


def _normalize_question(raw_question: Dict[str, Any], step_id: str, question_index: int) -> Dict[str, Any]:
    question_type = str(raw_question.get("question_type") or "")
    if question_type not in VALID_QUESTION_TYPES:
        raise ValueError(
            f"Question {question_index + 1} in step '{step_id}' has invalid question_type "
            f"'{question_type}'. Must be one of {VALID_QUESTION_TYPES}."
        )

    prompt = str(raw_question.get("prompt") or "").strip()
    if not prompt:
        raise ValueError(f"Question {question_index + 1} in step '{step_id}' is missing a 'prompt'.")

    question_id = str(raw_question.get("question_id") or f"{step_id}_q{question_index + 1}")

    normalized_question: Dict[str, Any] = {
        "question_id": question_id,
        "prompt": prompt,
        "question_type": question_type,
        "is_required": bool(raw_question.get("is_required", True)),
        "options": [],
        "likert_min_label": "",
        "likert_max_label": "",
    }

    if question_type in CHOICE_QUESTION_TYPES:
        normalized_question["options"] = _normalize_options(
            raw_options=raw_question.get("options"), step_id=step_id, question_id=question_id
        )
        if not normalized_question["options"]:
            raise ValueError(
                f"Question '{question_id}' in step '{step_id}' is a '{question_type}' question "
                f"but has no 'options' configured."
            )
    elif question_type == QUESTION_TYPE_LIKERT:
        likert_min = int(raw_question.get("likert_min", 1))
        likert_max = int(raw_question.get("likert_max", 5))
        if likert_min >= likert_max:
            raise ValueError(
                f"Question '{question_id}' in step '{step_id}' must have likert_min < likert_max."
            )
        normalized_question["options"] = _normalize_likert_options(likert_min, likert_max)
        normalized_question["likert_min_label"] = str(raw_question.get("likert_min_label") or "")
        normalized_question["likert_max_label"] = str(raw_question.get("likert_max_label") or "")

    return normalized_question


def normalize_questionnaire_questions(raw_questions: Optional[List[Dict[str, Any]]], step_id: str) -> List[Dict[str, Any]]:
    return [
        _normalize_question(raw_question=raw_question, step_id=step_id, question_index=question_index)
        for question_index, raw_question in enumerate(raw_questions or [])
    ]
