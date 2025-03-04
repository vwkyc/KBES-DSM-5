let isSubmitting = false;

function showLoading() {
    document.getElementById("loading").style.display = "flex";
}

function submitAnswer(severity) {
    if (isSubmitting) return;
    isSubmitting = true;
    showLoading();
    document.getElementById("answer").value = severity === "No" ? "no" : "yes";
    document.getElementById("severity").value = severity === "No" ? "None" : severity;
    document.getElementById("assessment-form").submit();
}

function goBack() {
    if (isSubmitting) return;
    isSubmitting = true;
    showLoading();
    window.location.href = "/ask?direction=back";
}
