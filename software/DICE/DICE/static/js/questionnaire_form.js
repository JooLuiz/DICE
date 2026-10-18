(function questionnaireForm() {
    const form = document.querySelector("form");
    const answersInput = document.getElementById("questionnaire_answers_json");

    if (!form || !answersInput) {
        return;
    }

    function collectAnswers() {
        const answers = {};

        document.querySelectorAll(".questionnaire-question").forEach(function (questionElement) {
            const questionId = questionElement.dataset.questionId;
            const questionType = questionElement.dataset.questionType;

            if (questionType === "multiple_choice") {
                answers[questionId] = Array.from(
                    questionElement.querySelectorAll('input[type="checkbox"]:checked')
                ).map(function (checkbox) {
                    return checkbox.value;
                });
            } else if (questionType === "open_text") {
                const textarea = questionElement.querySelector("textarea");
                answers[questionId] = textarea ? textarea.value : "";
            } else {
                const checkedRadio = questionElement.querySelector('input[type="radio"]:checked');
                answers[questionId] = checkedRadio ? checkedRadio.value : "";
            }
        });

        return answers;
    }

    function findUnansweredRequiredMultipleChoice() {
        // HTML's native "required" attribute cannot express "at least one checkbox checked",
        // so required multiple_choice questions need this explicit check before submit.
        const requiredMultipleChoiceQuestions = document.querySelectorAll(
            '.questionnaire-question[data-question-type="multiple_choice"][data-required="True"]'
        );

        return Array.from(requiredMultipleChoiceQuestions).find(function (questionElement) {
            return questionElement.querySelectorAll('input[type="checkbox"]:checked').length === 0;
        });
    }

    form.addEventListener("submit", function onQuestionnaireSubmit(submitEvent) {
        const unansweredMultipleChoice = findUnansweredRequiredMultipleChoice();
        if (unansweredMultipleChoice) {
            submitEvent.preventDefault();
            unansweredMultipleChoice.scrollIntoView({ behavior: "smooth", block: "center" });
            return;
        }

        answersInput.value = JSON.stringify(collectAnswers());
    });
})();
