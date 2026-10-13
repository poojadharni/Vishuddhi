
(function () {
    "use strict";

    const STORAGE_KEY = "vishuddhiPlantDiscoveryPrefs";

    const FIELD_ALIASES = {
        category: ["category", "plant category", "plant type"],
        care: ["care", "care level", "maintenance"],
        sunlight: ["sunlight", "sun light", "light"],
        purpose: ["purpose", "plant purpose", "use"]
    };

    function normalize(value) {
        return String(value || "")
            .trim()
            .toLowerCase()
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ");
    }

    function getPreferences() {
        try {
            const data = JSON.parse(
                localStorage.getItem(STORAGE_KEY) || "{}"
            );

            const preferences = {};

            Object.keys(FIELD_ALIASES).forEach(function (key) {
                const originalKey = Object.keys(data).find(
                    name => normalize(name) === key
                );

                if (!originalKey) return;

                const values = Array.isArray(data[originalKey])
                    ? data[originalKey]
                    : [data[originalKey]];

                // Select automatically only when one value was chosen.
                if (values.length === 1 && values[0]) {
                    preferences[key] = String(values[0]);
                }
            });

            return preferences;
        } catch (error) {
            console.warn("Could not read plant preferences", error);
            return {};
        }
    }

    function getLabel(select) {
        if (select.id) {
            const label = document.querySelector(
                'label[for="' +
                CSS.escape(select.id) +
                '"]'
            );

            if (label) return normalize(label.textContent);
        }

        const wrapper = select.closest(
            ".form-group, .frappe-control, .mb-3, .field"
        );

        const label = wrapper && wrapper.querySelector("label");

        return normalize(
            label?.textContent ||
            select.getAttribute("aria-label") ||
            select.name ||
            select.getAttribute("data-fieldname")
        );
    }

    function applyVariantPreferences() {
        const preferences = getPreferences();

        if (!Object.keys(preferences).length) return;

        const popups = document.querySelectorAll(
            ".modal.show, [role='dialog'], dialog[open]"
        );

        popups.forEach(function (popup) {
            popup.querySelectorAll("select").forEach(function (select) {
                if (select.disabled) return;

                const label = getLabel(select);

                const key = Object.keys(FIELD_ALIASES).find(
                    field => FIELD_ALIASES[field].some(
                        alias => normalize(alias) === label
                    )
                );

                if (!key || !preferences[key]) return;

                const desired = normalize(preferences[key]);

                const option = Array.from(select.options).find(
                    item => !item.disabled && (
                        normalize(item.textContent) === desired ||
                        normalize(item.value) === desired
                    )
                );

                if (!option) return;

                // Preserve an existing customer selection.
                const current = select.options[select.selectedIndex];

                if (
                    current &&
                    current.value &&
                    normalize(current.value) !== desired &&
                    normalize(current.textContent) !== desired
                ) {
                    return;
                }

                if (select.value === option.value) return;

                select.value = option.value;

                select.dispatchEvent(
                    new Event("change", { bubbles: true })
                );
            });
        });
    }

    function start() {
        const observer = new MutationObserver(
            applyVariantPreferences
        );

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        document.addEventListener("click", function () {
            setTimeout(applyVariantPreferences, 100);
            setTimeout(applyVariantPreferences, 500);
        }, true);

        applyVariantPreferences();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            start,
            { once: true }
        );
    } else {
        start();
    }
})();