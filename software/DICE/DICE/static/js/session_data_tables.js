/*
Renders the session Data tab as four labeled tables per round -- Interaction data, a collapsed
Internal questionnaire table (one column per question, pivoted from questionnaire_answers_json),
a collapsed External questionnaire table (callback bookkeeping), and a collapsed Other fields
table -- instead of oTree's single flat table.

Row data is fetched from oTree's existing ExportSessionWide CSV route and reshaped client-side
into the same "one row per round, values positional to a header list" structure that
`fieldHeadersByApp` already describes (see _templates/otree/SessionData.html for why we use that
route instead of SessionDataAjax, and why no backend view is overridden). dice_csv_parser.js does
the actual CSV decoding; this file only maps wide-CSV columns ("{app}.{round}.player.{field}") to
that structure and renders it.

Deliberately simplified vs. oTree's stock table-utils.js: every refresh fully re-renders the
visible tables rather than diffing cell-by-cell and flashing changed cells green, which keeps
this file legible at the cost of that "Updated N row(s)" messaging.
*/
(function () {
    "use strict";

    var config = window.DICE_SESSION_DATA_CONFIG;

    // Player fields that describe how a participant interacted with the feed itself.
    var INTERACTION_FIELDS = [
        "feed_condition", "sequence", "scroll_sequence", "viewport_data", "rowheight_data",
        "likes_data", "replies_data", "reposts_data", "promoted_post_clicks",
        "touch_capability", "device_type", "screen_resolution",
    ];

    // Player fields that describe questionnaire bookkeeping, aside from the raw answers blob.
    var QUESTIONNAIRE_STATIC_FIELDS = [
        "questionnaire_completion_mode", "callback_step_id", "callback_token",
        "callback_received", "callback_valid",
    ];

    var QUESTIONNAIRE_JSON_FIELD = "questionnaire_answers_json";

    // Shown first, pinned, in both the Interaction and Questionnaire tables.
    var IDENTITY_FIELDS = ["participant_code_display", "step_id"];

    var CELL_TRUNCATE_LENGTH = 40;

    function indexOfField(headers, fieldName) {
        return headers.indexOf(fieldName);
    }

    function parseQuestionnaireAnswers(rawValue) {
        if (!rawValue) {
            return {};
        }
        try {
            var parsed = JSON.parse(rawValue);
            return (parsed && typeof parsed === "object") ? parsed : {};
        } catch (parseError) {
            return {};
        }
    }

    function collectQuestionIds(rows, jsonColumnIndex) {
        var seen = [];
        var seenSet = {};
        rows.forEach(function (row) {
            var answers = parseQuestionnaireAnswers(row[jsonColumnIndex]);
            Object.keys(answers).forEach(function (questionId) {
                if (!seenSet[questionId]) {
                    seenSet[questionId] = true;
                    seen.push(questionId);
                }
            });
        });
        return seen;
    }

    function renderCellValue($cell, rawValue) {
        var displayValue = (rawValue === null || rawValue === undefined) ? "" : String(rawValue);
        if (displayValue.length <= CELL_TRUNCATE_LENGTH) {
            $cell.text(displayValue);
            return;
        }
        var $span = $("<span>")
            .addClass("dice-cell-value dice-cell-expandable")
            .text(displayValue.slice(0, CELL_TRUNCATE_LENGTH) + "…")
            .attr("data-bs-toggle", "popover")
            .attr("data-bs-trigger", "click")
            .attr("data-bs-content", displayValue);
        $cell.empty().append($span);
    }

    function buildHeaderRow(labels) {
        var $tr = $("<tr>");
        labels.forEach(function (label) {
            $tr.append($("<th>").text(label));
        });
        return $tr;
    }

    function buildStaticTable($table, headers, rows, columnIndices) {
        var $thead = $table.find("thead").empty();
        var $tbody = $table.find("tbody").empty();
        $thead.append(buildHeaderRow(columnIndices.map(function (i) { return headers[i]; })));
        rows.forEach(function (row) {
            var $tr = $("<tr>");
            columnIndices.forEach(function (columnIndex) {
                var $td = $("<td>");
                renderCellValue($td, row[columnIndex]);
                $tr.append($td);
            });
            $tbody.append($tr);
        });
    }

    function buildQuestionnaireTable($table, headers, rows, identityIndices, staticIndices, jsonIndex) {
        var questionIds = jsonIndex === -1 ? [] : collectQuestionIds(rows, jsonIndex);
        var columnLabels = identityIndices.map(function (i) { return headers[i]; })
            .concat(staticIndices.map(function (i) { return headers[i]; }))
            .concat(questionIds);

        var $thead = $table.find("thead").empty();
        var $tbody = $table.find("tbody").empty();
        $thead.append(buildHeaderRow(columnLabels));

        rows.forEach(function (row) {
            var $tr = $("<tr>");
            identityIndices.concat(staticIndices).forEach(function (columnIndex) {
                var $td = $("<td>");
                renderCellValue($td, row[columnIndex]);
                $tr.append($td);
            });
            var answers = jsonIndex === -1 ? {} : parseQuestionnaireAnswers(row[jsonIndex]);
            questionIds.forEach(function (questionId) {
                var $td = $("<td>");
                var answerValue = answers[questionId];
                renderCellValue($td, Array.isArray(answerValue) ? answerValue.join(", ") : answerValue);
                $tr.append($td);
            });
            $tbody.append($tr);
        });
    }

    function renderRoundGroup($group, headers, rows) {
        var identityIndices = IDENTITY_FIELDS.map(function (f) { return indexOfField(headers, f); })
            .filter(function (i) { return i !== -1; });
        var interactionIndices = identityIndices.concat(
            INTERACTION_FIELDS.map(function (f) { return indexOfField(headers, f); }).filter(function (i) { return i !== -1; })
        );
        var questionnaireStaticIndices = QUESTIONNAIRE_STATIC_FIELDS
            .map(function (f) { return indexOfField(headers, f); })
            .filter(function (i) { return i !== -1; });
        var questionnaireJsonIndex = indexOfField(headers, QUESTIONNAIRE_JSON_FIELD);

        var groupedIndices = {};
        identityIndices.concat(interactionIndices, questionnaireStaticIndices, [questionnaireJsonIndex])
            .forEach(function (i) { groupedIndices[i] = true; });
        var otherIndices = headers.map(function (_, i) { return i; }).filter(function (i) { return !groupedIndices[i]; });

        buildStaticTable($group.find(".dice-interaction-table"), headers, rows, interactionIndices);
        buildQuestionnaireTable(
            $group.find(".dice-questionnaire-internal-table"), headers, rows,
            identityIndices, [], questionnaireJsonIndex
        );
        buildStaticTable(
            $group.find(".dice-questionnaire-external-table"), headers, rows,
            identityIndices.concat(questionnaireStaticIndices)
        );
        buildStaticTable($group.find(".dice-other-table"), headers, rows, otherIndices);

        $group.find('[data-bs-toggle="popover"]').popover();
    }

    function renderAllRounds(rowsByRound) {
        var $groups = $(".dice-round-group");
        for (var roundIndex = 0; roundIndex < rowsByRound.length; roundIndex++) {
            var appName = config.appNamesBySubsession[roundIndex];
            var headers = config.fieldHeadersByApp[appName];
            renderRoundGroup($groups.eq(roundIndex), headers, rowsByRound[roundIndex]);
        }
    }

    var visibleRoundIndex = 0;

    function updateVisibility() {
        var $groups = $(".dice-round-group");
        $groups.hide().eq(visibleRoundIndex).show();
        var curApp = config.appNamesBySubsession[visibleRoundIndex];
        var curRound = config.roundNumbersBySubsession[visibleRoundIndex];
        $("#cur-app").text(curApp);
        $("#cur-round").text(curRound);
        $("#app-prev").prop("disabled", curApp === config.appNamesBySubsession[0]);
        $("#app-next").prop("disabled", curApp === config.appNamesBySubsession[config.appNamesBySubsession.length - 1]);
        $("#round-prev").prop("disabled", visibleRoundIndex === 0);
        $("#round-next").prop("disabled", visibleRoundIndex === $groups.length - 1);
    }

    function bindNavigation() {
        $("#app-prev").on("click", function () {
            var curApp = config.appNamesBySubsession[visibleRoundIndex];
            for (var i = visibleRoundIndex - 1; i >= 0; i--) {
                if (config.appNamesBySubsession[i] !== curApp && config.roundNumbersBySubsession[i] === 1) {
                    visibleRoundIndex = i;
                    break;
                }
            }
            updateVisibility();
        });
        $("#app-next").on("click", function () {
            var curApp = config.appNamesBySubsession[visibleRoundIndex];
            for (var i = visibleRoundIndex + 1; i < config.appNamesBySubsession.length; i++) {
                if (config.appNamesBySubsession[i] !== curApp) {
                    visibleRoundIndex = i;
                    break;
                }
            }
            updateVisibility();
        });
        $("#round-prev").on("click", function () {
            if (visibleRoundIndex > 0) visibleRoundIndex--;
            updateVisibility();
        });
        $("#round-next").on("click", function () {
            if (visibleRoundIndex < $(".dice-round-group").length - 1) visibleRoundIndex++;
            updateVisibility();
        });
        $("#btn-refresh").on("click", function () {
            fetchAndRender(true);
        });
    }

    function fetchAndRender(isRefresh) {
        $.ajax({
            url: config.wideExportUrl,
            type: "GET",
            dataType: "text",
            error: function () {
                $("#server_error").show();
            },
            success: function (csvText) {
                $("#server_error").hide();
                var rowsByRound = window.DiceWideCsvMapper.mapCsvToRowsByRound(
                    csvText, config.roundNumbersBySubsession, config.appNamesBySubsession, config.fieldHeadersByApp
                );
                renderAllRounds(rowsByRound);
                if (isRefresh) {
                    $("#msg-refreshed").stop(true, true).text("Refreshed").show().fadeOut(5000);
                }
            },
        });
    }

    $(function () {
        bindNavigation();
        updateVisibility();
        fetchAndRender(false);
    });
})();
