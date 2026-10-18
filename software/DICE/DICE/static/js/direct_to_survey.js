(function questionnaireBridge() {
    const surveyLink = js_vars.survey_link || "";
    const returnParamName = js_vars.return_param_name || "return_url";
    const callbackFlagParam = js_vars.callback_flag_param || "journey_cb";
    const callbackStepParam = js_vars.callback_step_param || "journey_step_id";
    const callbackTokenParam = js_vars.callback_token_param || "journey_token";
    const callbackStepId = js_vars.callback_step_id || "";
    const callbackToken = js_vars.callback_token || "";
    const launchDelayMs = Number(js_vars.launch_delay_ms || 1200);

    const bridgeForm = document.querySelector("form");
    const completionModeInput = document.getElementById("questionnaire_completion_mode");
    const callbackStepIdInput = document.getElementById("callback_step_id");
    const callbackTokenInput = document.getElementById("callback_token");
    const callbackReceivedInput = document.getElementById("callback_received");
    const manualCompleteButton = document.getElementById("manual-complete-button");
    const openSurveyLinkButton = document.getElementById("open-survey-link");

    function submitBridgeForm(mode, callbackReceived, stepId, token) {
        if (!bridgeForm || !completionModeInput || !callbackReceivedInput || !callbackStepIdInput || !callbackTokenInput) {
            return;
        }
        completionModeInput.value = mode;
        callbackReceivedInput.value = callbackReceived;
        callbackStepIdInput.value = stepId;
        callbackTokenInput.value = token;
        bridgeForm.submit();
    }

    function buildCallbackUrl() {
        const callbackUrl = new URL(window.location.href);
        callbackUrl.search = "";
        callbackUrl.searchParams.set(callbackFlagParam, "1");
        callbackUrl.searchParams.set(callbackStepParam, callbackStepId);
        callbackUrl.searchParams.set(callbackTokenParam, callbackToken);
        return callbackUrl.toString();
    }

    function buildSurveyLinkWithCallback() {
        if (!surveyLink) {
            return "";
        }

        let surveyUrl;
        try {
            surveyUrl = new URL(surveyLink);
        } catch (invalidAbsoluteUrlError) {
            surveyUrl = new URL(surveyLink, window.location.origin);
        }

        surveyUrl.searchParams.set(returnParamName, buildCallbackUrl());
        return surveyUrl.toString();
    }

    const queryParameters = new URLSearchParams(window.location.search);
    const isCallbackRequest = queryParameters.get(callbackFlagParam) === "1";
    if (isCallbackRequest) {
        submitBridgeForm(
            "auto_callback",
            "1",
            queryParameters.get(callbackStepParam) || "",
            queryParameters.get(callbackTokenParam) || "",
        );
        return;
    }

    const questionnaireLink = buildSurveyLinkWithCallback();

    if (openSurveyLinkButton && questionnaireLink) {
        openSurveyLinkButton.href = questionnaireLink;
    }

    if (manualCompleteButton) {
        manualCompleteButton.addEventListener("click", function onManualCompleteClick() {
            submitBridgeForm("manual_fallback", "0", "", "");
        });
    }

    if (questionnaireLink) {
        window.setTimeout(function triggerQuestionnaireRedirect() {
            window.location.assign(questionnaireLink);
        }, launchDelayMs);
    }
})();
