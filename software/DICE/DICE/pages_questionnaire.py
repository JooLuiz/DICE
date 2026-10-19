"""E_Questionnaire: renders and records answers for in-system (non-external) questionnaire steps.

Kept in its own module to avoid growing DICE/__init__.py further. Because oTree treats this
app's package __init__.py as both the models and pages module ("noself" apps), the names this
page depends on (C, _step_config, is_active_round) are imported lazily inside each method body
rather than at module import time, so import order relative to __init__.py never matters.
"""
from otree.api import Page

from .questionnaire_bridge import mark_step_completion
from .questionnaire_models import save_questionnaire_responses


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
        return dict(questions=step_config.get("questionnaire_questions", []))

    @staticmethod
    def before_next_page(player, timeout_happened):
        from . import _step_config

        step_config = _step_config(player) or {}
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
