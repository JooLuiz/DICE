/*
Minimal RFC 4126-style CSV parser for the Data tab (see session_data_tables.js).

oTree's wide-export CSV (ExportSessionWide) is the only existing route that returns full,
untruncated row data -- its field values can contain commas, newlines, and double quotes (e.g.
the JSON-encoded questionnaire_answers_json blob), so a plain `split(",")` is not safe. This
parser only needs to handle standard double-quote escaping ("" inside a quoted field), which is
exactly what Python's csv module (used to write the export) produces.
*/
window.DiceCsvParser = (function () {
    "use strict";

    function parseRows(csvText) {
        var rows = [];
        var currentRow = [];
        var currentField = "";
        var insideQuotes = false;

        for (var i = 0; i < csvText.length; i++) {
            var character = csvText[i];

            if (insideQuotes) {
                if (character === '"' && csvText[i + 1] === '"') {
                    currentField += '"';
                    i++;
                } else if (character === '"') {
                    insideQuotes = false;
                } else {
                    currentField += character;
                }
                continue;
            }

            if (character === '"') {
                insideQuotes = true;
            } else if (character === ",") {
                currentRow.push(currentField);
                currentField = "";
            } else if (character === "\r") {
                // skip; \n (below) ends the row
            } else if (character === "\n") {
                currentRow.push(currentField);
                rows.push(currentRow);
                currentRow = [];
                currentField = "";
            } else {
                currentField += character;
            }
        }

        if (currentField.length > 0 || currentRow.length > 0) {
            currentRow.push(currentField);
            rows.push(currentRow);
        }

        return rows;
    }

    function parse(csvText) {
        var allRows = parseRows(csvText).filter(function (row) {
            return !(row.length === 1 && row[0] === "");
        });
        return {
            header: allRows[0] || [],
            rows: allRows.slice(1),
        };
    }

    return { parse: parse };
})();
