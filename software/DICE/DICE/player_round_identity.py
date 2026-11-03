"""Assigns the round identity shown on the session Data tab.

Role: writes step_id and participant_code_display onto a Player for every journey round.
Not in this file: feed preparation, questionnaire answer storage, and the label-versus-code rule.
Key dependencies: DICE.ui_strings.resolve_participant_display_id.
See also: software/DICE/tests/test_player_round_identity.py, software/DICE/DICE/__init__.py.
"""
from typing import Mapping, Optional, Protocol

from .ui_strings import resolve_participant_display_id


class _ParticipantIdentity(Protocol):
    code: Optional[str]
    label: Optional[str]


class _RoundIdentityPlayer(Protocol):
    step_id: str
    participant_code_display: Optional[str]
    participant: _ParticipantIdentity


def assign_round_identity(
    player: _RoundIdentityPlayer,
    step_config: Optional[Mapping[str, object]],
) -> None:
    """Writes this round's step id and participant display label onto the player.

    Args:
        player: oTree Player, or any object with step_id, participant_code_display, and participant.
        step_config: Normalized journey step. None leaves the player unchanged.

    Returns:
        None.

    Side effects:
        Mutates player.step_id and player.participant_code_display when step_config is present.
    """
    if not step_config:
        return
    player.step_id = str(step_config.get("step_id") or "")
    participant = player.participant
    player.participant_code_display = resolve_participant_display_id(
        participant.code,
        participant.label,
    )
