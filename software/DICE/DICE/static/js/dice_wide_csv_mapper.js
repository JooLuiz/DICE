/*
Reshapes oTree's wide-export CSV (one row per participant, one column per
"{app}.{round}.{player|group|subsession}.{field}") into the same "array of rounds, each an array
of player-rows positional to a header list" structure that session_data_tables.js already expects
from the stock AJAX payload shape. See _templates/otree/SessionData.html and
session_data_tables.js for why the wide-export route is used instead of SessionDataAjax.

Field-to-model-level mapping is hardcoded here rather than fetched from the server: every DICE
session config (Twitter, Instagram, Stories, Linkedin, Generic) shares the exact same DICE/
models module, so the Player/Group/Subsession field names -- and therefore which CSV column
prefix each belongs to -- are the same regardless of which config created the session.
*/
window.DiceWideCsvMapper = (function () {
    "use strict";

    // oTree's own built-in Player fields (see otree/export.py's _get_table_fields); "group" has
    // no corresponding wide-export column (it's a synthetic pfield, redundant with
    // id_in_subsession), so it's intentionally left unmapped below.
    var BUILTIN_PLAYER_FIELDS = ["id_in_group", "role", "payoff"];
    var BUILTIN_GROUP_FIELDS = ["id_in_subsession"];

    function csvColumnPrefixForField(fieldName) {
        if (fieldName === "group") {
            return null;
        }
        if (BUILTIN_GROUP_FIELDS.indexOf(fieldName) !== -1) {
            return "group";
        }
        if (BUILTIN_PLAYER_FIELDS.indexOf(fieldName) !== -1) {
            return "player";
        }
        // Every other field in fieldHeadersByApp is one of DICE's own declared Player fields
        // (tracked via get_form_fields/the Player model) or a Subsession field (feed_conditions,
        // FEED); DICE declares no custom Group fields, so anything left over is a Player field
        // unless it's one of the two known Subsession fields.
        if (fieldName === "feed_conditions" || fieldName === "FEED") {
            return "subsession";
        }
        return "player";
    }

    function buildColumnIndexByName(header) {
        var columnIndexByName = {};
        header.forEach(function (columnName, index) {
            columnIndexByName[columnName] = index;
        });
        return columnIndexByName;
    }

    function mapCsvToRowsByRound(csvText, roundNumbersBySubsession, appNamesBySubsession, fieldHeadersByApp) {
        var parsed = window.DiceCsvParser.parse(csvText);
        var columnIndexByName = buildColumnIndexByName(parsed.header);

        return roundNumbersBySubsession.map(function (roundNumber, roundIndex) {
            var appName = appNamesBySubsession[roundIndex];
            var headers = fieldHeadersByApp[appName];

            return parsed.rows.map(function (participantCsvRow) {
                return headers.map(function (fieldName) {
                    var prefix = csvColumnPrefixForField(fieldName);
                    if (!prefix) {
                        return "";
                    }
                    var columnName = appName + "." + roundNumber + "." + prefix + "." + fieldName;
                    var columnIndex = columnIndexByName[columnName];
                    return columnIndex === undefined ? "" : participantCsvRow[columnIndex];
                });
            });
        });
    }

    return { mapCsvToRowsByRound: mapCsvToRowsByRound };
})();
