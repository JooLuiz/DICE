"""Journey-step title normalization and numbered session-form fields."""
import unittest

from DICE.journey_config import resolve_journey_steps
from session_config_steps import build_steps_from_numbered_fields


def _internal_question():
    return [{"question_type": "open_text", "prompt": "Thoughts?"}]


class JourneyTitleNormalizationTests(unittest.TestCase):
    def test_blank_title_normalizes_to_an_empty_string(self):
        # The page resolver treats an empty title as "use the session language default".
        steps = resolve_journey_steps(
            {
                "journey_steps": [
                    {
                        "step_id": "step_1",
                        "questionnaire_mode": "internal",
                        "questionnaire_questions": _internal_question(),
                    }
                ],
            },
            max_supported_steps=6,
        )
        self.assertEqual(steps[0]["questionnaire_title"], "")

    def test_configured_title_is_stripped(self):
        # Surrounding whitespace must not become part of the heading.
        steps = resolve_journey_steps(
            {
                "journey_steps": [
                    {
                        "questionnaire_mode": "internal",
                        "questionnaire_title": "  Feedback  ",
                        "questionnaire_questions": _internal_question(),
                    }
                ],
            },
            max_supported_steps=6,
        )
        self.assertEqual(steps[0]["questionnaire_title"], "Feedback")


class NumberedFieldTitleTests(unittest.TestCase):
    def test_copies_title_onto_a_questionnaire_only_step(self):
        # The /sessions form stores the title beside the questions JSON, not inside it.
        steps = build_steps_from_numbered_fields(
            {
                "channel_type": "Insta",
                "step_1_questionnaire_json": '[{"question_type": "open_text", "prompt": "Hi"}]',
                "step_1_questionnaire_title": "Minha pesquisa",
            }
        )
        self.assertEqual(steps[0]["questionnaire_title"], "Minha pesquisa")
        self.assertEqual(steps[0]["questionnaire_mode"], "internal")

    def test_title_alone_does_not_create_a_step(self):
        # A heading without questions, a feed, or a survey link is an unused slot.
        steps = build_steps_from_numbered_fields(
            {"step_1_questionnaire_title": "Unused heading"}
        )
        self.assertEqual(steps, [])


if __name__ == "__main__":
    unittest.main()
