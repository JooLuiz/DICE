"""Wide-CSV ordering for numbered journey-step config columns."""
import unittest

from wide_export_columns import STEP_FIELD_SUFFIXES, reorder_step_config_columns


class StepFieldSuffixTests(unittest.TestCase):
    def test_questionnaire_title_follows_questions_json(self):
        # The Data export groups each slot's title with that slot's other fields.
        self.assertEqual(
            STEP_FIELD_SUFFIXES,
            ("feed_csv_url", "survey_link", "questionnaire_json", "questionnaire_title"),
        )


class ReorderStepConfigColumnsTests(unittest.TestCase):
    def test_sorts_a_title_column_into_slot_order(self):
        # oTree may emit step fields out of slot order; titles must travel with their slot.
        header = [
            "session.code",
            "session.config.step_2_questionnaire_title",
            "session.config.step_1_questionnaire_json",
            "session.config.step_1_questionnaire_title",
        ]
        rows = [header, ["s1", "Second title", "[]", "First title"]]
        reordered = reorder_step_config_columns(rows)
        self.assertEqual(
            reordered[0],
            [
                "session.code",
                "session.config.step_1_questionnaire_json",
                "session.config.step_1_questionnaire_title",
                "session.config.step_2_questionnaire_title",
            ],
        )
        self.assertEqual(reordered[1], ["s1", "[]", "First title", "Second title"])


if __name__ == "__main__":
    unittest.main()
