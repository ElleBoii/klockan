function setupAutocomplete(searchInputId, listId, selectId) {
    const searchInput = document.getElementById(searchInputId);
    const list = document.getElementById(listId);
    const select = document.getElementById(selectId);

    const options = Array.from(select.options)
        .filter(function (o) { return o.value !== ""; })
        .map(function (o) { return { value: o.value, label: o.text.trim() }; });

    // Pre-fill the text input if a value is already selected (e.g. after page reload with filter active)
    if (select.value) {
        const selected = options.find(function (o) { return o.value === select.value; });
        if (selected) searchInput.value = selected.label;
    }

    function showMatches(query) {
        list.innerHTML = "";
        const q = query.toLowerCase().trim();
        const matches = q ? options.filter(function (o) { return o.label.toLowerCase().includes(q); }) : [];

        if (matches.length === 0) {
            list.hidden = true;
            return;
        }

        matches.forEach(function (option) {
            const item = document.createElement("div");
            item.className = "autocomplete-item";
            item.textContent = option.label;
            item.addEventListener("mousedown", function (e) {
                e.preventDefault(); // keep focus on input so blur doesn't fire first
                searchInput.value = option.label;
                select.value = option.value;
                list.hidden = true;
            });
            list.appendChild(item);
        });

        list.hidden = false;
    }

    searchInput.addEventListener("input", function () {
        if (!this.value.trim()) {
            select.value = "";
            list.hidden = true;
            return;
        }
        showMatches(this.value);
    });

    searchInput.addEventListener("focus", function () {
        if (this.value.trim()) showMatches(this.value);
    });

    searchInput.addEventListener("blur", function () {
        list.hidden = true;
        // If what's typed doesn't match the current selection, snap back to it (or clear)
        const current = options.find(function (o) { return o.value === select.value; });
        if (!current || current.label !== this.value) {
            this.value = current ? current.label : "";
            if (!current) select.value = "";
        }
    });
}
