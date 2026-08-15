document.addEventListener("DOMContentLoaded", () => {
    // -----------------------------
    // Issue click -> scroll to story
    // -----------------------------
    const issueItems = document.querySelectorAll("[data-story-target]");

    issueItems.forEach(item => {
        item.addEventListener("click", (e) => {
            const targetId = item.getAttribute("data-story-target");
            if (!targetId) return;

            const target = document.getElementById(targetId);
            if (!target) return;

            e.preventDefault();

            document.querySelectorAll(".story-card.active-story").forEach(card => {
                card.classList.remove("active-story");
            });

            target.classList.add("active-story");

            target.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

            setTimeout(() => {
                target.classList.remove("active-story");
            }, 2500);
        });
    });

    // -----------------------------
    // Toggle case-related warnings
    // -----------------------------
    const toggleCaseWarnings = document.getElementById("toggle-case-warnings");

    function applyCaseWarningVisibility() {
        if (!toggleCaseWarnings) return;

        const showCaseWarnings = toggleCaseWarnings.checked;
        const caseWarningElements = document.querySelectorAll('[data-case-warning="true"]');

        caseWarningElements.forEach(el => {
            el.style.display = showCaseWarnings ? "" : "none";
        });
    }

    if (toggleCaseWarnings) {
        toggleCaseWarnings.checked = false;
        applyCaseWarningVisibility();
        toggleCaseWarnings.addEventListener("change", applyCaseWarningVisibility);
    }

    // -----------------------------
    // Direct JSON form UX
    // -----------------------------
    const jsonText = document.getElementById("json_text");
    const jsonFile = document.getElementById("json_file");
    const clearJsonFileBtn = document.getElementById("clear_json_file");

    function updateJsonInputState() {
        if (!jsonText || !jsonFile) return;

        const hasText = jsonText.value.trim().length > 0;
        const hasFile = jsonFile.files && jsonFile.files.length > 0;

        if (hasText) {
            jsonFile.disabled = true;
            if (clearJsonFileBtn) clearJsonFileBtn.disabled = true;
            jsonText.disabled = false;
        } else if (hasFile) {
            jsonText.disabled = true;
            jsonFile.disabled = false;
            if (clearJsonFileBtn) clearJsonFileBtn.disabled = false;
        } else {
            jsonText.disabled = false;
            jsonFile.disabled = false;
            if (clearJsonFileBtn) clearJsonFileBtn.disabled = true;
        }
    }

    if (jsonText && jsonFile) {
        jsonText.addEventListener("input", updateJsonInputState);

        jsonFile.addEventListener("change", () => {
            if (jsonFile.files && jsonFile.files.length > 0) {
                jsonText.value = "";
            }
            updateJsonInputState();
        });

        if (clearJsonFileBtn) {
            clearJsonFileBtn.addEventListener("click", () => {
                jsonFile.value = "";
                jsonText.disabled = false;
                updateJsonInputState();
            });
        }

        updateJsonInputState();
    }
});