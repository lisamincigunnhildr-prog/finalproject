document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // PHONE LIMIT (11 DIGITS)
    // =========================
   const phoneInput =
    document.getElementById("number-input") ||  document.getElementById("contact_number") ||
    document.querySelector(".number-input");

    if (phoneInput) {

        phoneInput.setAttribute("maxlength", "11");

        phoneInput.addEventListener("input", function () {
            this.value = this.value.replace(/\D/g, "").slice(0, 11);
        });
    }


    // =========================
    // PASSWORD TOGGLE (REUSABLE)
    // =========================
    function addToggle(inputId) {

        const input = document.getElementById(inputId);
        if (!input) return;

        const wrapper = input.closest(".password-box") || input.parentElement;

        // prevent duplicate icon
        if (wrapper.querySelector(".toggle-eye")) return;

        const icon = document.createElement("i");
        icon.className = "fa-solid fa-eye toggle-eye";

        icon.style.position = "absolute";
        icon.style.right = "15px";
        icon.style.top = "50%";
        icon.style.transform = "translateY(-50%)";
        icon.style.cursor = "pointer";
        icon.style.color = "#666";

        wrapper.style.position = "relative";
        wrapper.appendChild(icon);

        let visible = false;

        icon.addEventListener("click", function () {
            visible = !visible;
            input.type = visible ? "text" : "password";

            icon.className = visible
                ? "fa-solid fa-eye-slash toggle-eye"
                : "fa-solid fa-eye toggle-eye";
        });
    }

    // works for register + profile
    addToggle("password");
    addToggle("confirm_password");
    addToggle("confirmpass");


    // =========================
    // PASSWORD MATCH CHECK
    // =========================
   const password = document.getElementById("password");

const confirmPassword =
    document.getElementById("confirm_password") ||
    document.getElementById("confirmpass");

if (password && confirmPassword) {

    // REMOVE OLD MESSAGE IF EXISTS
    const existingMsg = confirmPassword.parentElement.querySelector(".match-msg");
    if (existingMsg) existingMsg.remove();

    const matchMsg = document.createElement("small");
    matchMsg.className = "match-msg";
    matchMsg.style.display = "block";
    matchMsg.style.marginTop = "5px";
    matchMsg.style.fontWeight = "500";

    confirmPassword.parentElement.appendChild(matchMsg);

    function checkMatch() {

        if (!confirmPassword.value) {
            matchMsg.textContent = "";
            return;
        }

        if (password.value === confirmPassword.value) {
            matchMsg.textContent = "Passwords match";
            matchMsg.style.color = "green";
        } else {
            matchMsg.textContent = "Passwords do not match";
            matchMsg.style.color = "red";
        }
    }

    password.addEventListener("input", checkMatch);
    confirmPassword.addEventListener("input", checkMatch);
}
});