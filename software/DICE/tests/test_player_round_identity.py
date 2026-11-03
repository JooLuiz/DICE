"""Round identity written for feed and questionnaire-only steps."""
import unittest
from types import SimpleNamespace

from DICE.player_round_identity import assign_round_identity


def _player(code="CODE123", label=None):
    return SimpleNamespace(
        step_id="",
        participant_code_display="",
        participant=SimpleNamespace(code=code, label=label),
    )


class AssignRoundIdentityTests(unittest.TestCase):
    def test_questionnaire_only_step_records_code_when_label_is_missing(self):
        # Questionnaire-only rounds never open the feed page, so creation must still stamp identity.
        player = _player()
        assign_round_identity(player, {"step_id": "step_1"})
        self.assertEqual(player.step_id, "step_1")
        self.assertEqual(player.participant_code_display, "CODE123")

    def test_later_completion_prefers_a_participant_label(self):
        # A label can arrive after session creation; completing the step refreshes the display value.
        player = _player(label="PROLIFIC_ID")
        assign_round_identity(player, {"step_id": "step_3"})
        self.assertEqual(player.step_id, "step_3")
        self.assertEqual(player.participant_code_display, "PROLIFIC_ID")

    def test_missing_step_leaves_the_player_unchanged(self):
        # Inactive rounds have no step config and must not clear an existing identity.
        player = _player()
        player.step_id = "already-set"
        player.participant_code_display = "already-set"
        assign_round_identity(player, None)
        self.assertEqual(player.step_id, "already-set")
        self.assertEqual(player.participant_code_display, "already-set")


if __name__ == "__main__":
    unittest.main()
