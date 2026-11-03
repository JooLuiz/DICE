"""Renders and records answers for in-system questionnaire steps.

Role: oTree page shown when a journey step uses questionnaire_mode="internal".
Not in this file: question schema validation and response-row export.
Key dependencies: otree, DICE.questionnaire_models, DICE.player_round_identity, DICE.ui_strings.
See also: software/DICE/DICE/E_Questionnaire.html.

Because oTree treats this app's package __init__.py as both the models and pages module
("noself" apps), C, _step_config, and is_active_round are imported inside each method so
import order relative to __init__.py never matters.
"""
from otree.api import Page

from .player_round_identity import assign_round_identity
from .questionnaire_bridge import mark_step_completion
from .questionnaire_models import save_questionnaire_responses
from .ui_strings import resolve_questionnaire_title


class E_Questionnaire(Page):
    form_model = "player"
    form_fields = ["questionnaire_answers_json"]

    @staticmethod
    def is_displayed(player):
        from . import C, _step_config, is_active_round

        if not is_active_round(player.session, player.round_number, C.NUM_ROUNDS):
            return False
        step_config = _step_config(player) or {}
        return step_config.get("questionnaire_mode", "external") == "internal"

    @staticmethod
    def vars_for_template(player):
        from . import _step_config

        step_config = _step_config(player) or {}
        return dict(
            questions=step_config.get("questionnaire_questions", []),
            questionnaire_title=resolve_questionnaire_title(
                language=player.session.config.get("language", "en"),
                configured_title=step_config.get("questionnaire_title"),
            ),
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        from . import _step_config

        step_config = _step_config(player) or {}
        assign_round_identity(player, step_config)
        save_questionnaire_responses(player=player, step_config=step_config)
        # Mirrors D_Redirect's completion bookkeeping for the external-survey flow, so
        # journey_completed_steps reliably reflects "did this participant finish this step"
        # regardless of questionnaire_mode -- needed to identify partial-journey drop-off.
        mark_step_completion(
            player=player,
            step_id=str(step_config.get("step_id") or ""),
            completion_mode="internal_submitted",
            callback_valid=True,
        )
