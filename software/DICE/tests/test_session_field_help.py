"""Tests for create-session labels, field explanations, and the sessions list."""
import unittest
from pathlib import Path

from otree.session import SessionConfig

from session_field_help import help_text, normalize_session_label


class SessionLabelTests(unittest.TestCase):
    def test_posted_label_is_stripped(self):
        self.assertEqual(normalize_session_label("  Forum pilot  "), "Forum pilot")

    def test_blank_label_stays_empty(self):
        self.assertEqual(normalize_session_label("   "), "")
        self.assertEqual(normalize_session_label(None), "")
        self.assertEqual(normalize_session_label([""]), "")


class SessionFieldHelpTests(unittest.TestCase):
    def test_generated_field_places_help_below_the_label(self):
        # The explanation belongs in the label cell, before the input cell.
        config = SessionConfig(name="Instagram", study_name="Pilot study")
        html = config.editable_field_html("study_name")
        label_at = html.find("<b>study_name</b>")
        help_at = html.find("session-field-help")
        input_at = html.find("<input")

        self.assertLess(label_at, help_at)
        self.assertLess(help_at, input_at)
        self.assertIn(help_text("study_name"), html)

    def test_journey_slot_uses_the_shared_step_explanation(self):
        self.assertEqual(
            help_text("step_3_questionnaire_title"),
            help_text("step_questionnaire_title"),
        )


class CreateSessionHelpPresentationTests(unittest.TestCase):
    def test_top_fields_use_tooltips_and_lower_fields_keep_text(self):
        template = Path(__file__).resolve().parents[1].joinpath(
            "_templates", "otree", "includes", "CreateSessionForm.html"
        ).read_text(encoding="utf-8")

        self.assertEqual(template.count('class="session-field-info"'), 3)
        self.assertIn('data-bs-title="{{ field_help.session_config }}"', template)
        self.assertIn('data-bs-title="{{ field_help.num_participants }}"', template)
        self.assertIn('data-bs-title="{{ field_help.label }}"', template)
        self.assertIn(
            '<div class="session-field-help">{{ field_help.language }}</div>',
            template,
        )
    def test_sessions_table_shows_study_name_and_label(self):
        template = Path(__file__).resolve().parents[1].joinpath(
            "_templates", "otree", "Sessions.html"
        ).read_text(encoding="utf-8")

        self.assertIn("<th>Study name</th>", template)
        self.assertIn("<th>Label</th>", template)
        self.assertIn("{{ s.config.study_name }}", template)
        self.assertIn("{{ s.label }}", template)

    def test_session_heading_shows_study_name_and_label(self):
        template = Path(__file__).resolve().parents[1].joinpath(
            "_templates", "otree", "Session.html"
        ).read_text(encoding="utf-8")

        self.assertIn('class="session-heading-meta"', template)
        self.assertIn("{{ session.config.study_name }}", template)
        self.assertIn("{{ session.label }}", template)

    def test_rooms_list_shows_the_session_label_before_the_code(self):
        template = Path(__file__).resolve().parents[1].joinpath(
            "_templates", "otree", "Rooms.html"
        ).read_text(encoding="utf-8")
        label_at = template.find("{{ session.label }}")
        code_link_at = template.find("{% url 'SessionMonitor' session.code %}")

        self.assertGreaterEqual(label_at, 0)
        self.assertLess(label_at, code_link_at)


if __name__ == "__main__":
    unittest.main()
