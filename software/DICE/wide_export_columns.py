"""Puts wide-CSV journey step columns back into slot order.

Role: reorders `session.config.step_*` columns in oTree's wide CSV after `get_rows_for_wide_csv` builds them.
Not in this file: round columns (`DICE.N.*`) and the Data tab tables, which read columns by name.
Key dependencies: `otree.export.get_rows_for_wide_csv`, wrapped in place when this module is imported.
See also: software/DICE/settings.py (the step field suffixes are declared in the same order).
"""
import re

import otree.export

# Same suffix order as the step_N_* fields built in settings.SESSION_CONFIG_DEFAULTS.
STEP_FIELD_SUFFIXES = ("feed_csv_url", "survey_link", "questionnaire_json")

_STEP_COLUMN = re.compile(
    r"^session\.config\.step_(\d+)_(" + "|".join(STEP_FIELD_SUFFIXES) + r")$"
)


def reorder_step_config_columns(rows):
    """Returns rows with step config columns sorted by slot number, then suffix.

    Other columns stay in their original positions. An empty oTree export (`[[]]`) is unchanged.
    """
    if not rows or not rows[0]:
        return rows

    header = rows[0]
    step_positions = []
    sortable_columns = []
    for index, column_name in enumerate(header):
        match = _STEP_COLUMN.match(str(column_name))
        if not match:
            continue
        slot_number = int(match.group(1))
        suffix_order = STEP_FIELD_SUFFIXES.index(match.group(2))
        step_positions.append(index)
        sortable_columns.append((slot_number, suffix_order, index))

    if len(step_positions) < 2:
        return rows

    sortable_columns.sort()
    source_indexes = [item[2] for item in sortable_columns]
    if source_indexes == step_positions:
        return rows

    for row in rows:
        ordered_values = [row[index] for index in source_indexes]
        for position, value in zip(step_positions, ordered_values):
            row[position] = value
    return rows


def install():
    """Wraps oTree's wide-CSV row builder once. Later imports do not wrap again."""
    export_module = otree.export
    current = export_module.get_rows_for_wide_csv
    if getattr(current, "_dice_step_order_installed", False):
        return

    def get_rows_for_wide_csv(session_code=None):
        return reorder_step_config_columns(current(session_code=session_code))

    get_rows_for_wide_csv._dice_step_order_installed = True
    export_module.get_rows_for_wide_csv = get_rows_for_wide_csv


install()
