// Collapsible edit panel. Click a node on the DAG (see canvas.js's click
// handler, which calls onNodeSelected below) to populate this form with its
// data. Not wired to the backend yet — field changes just log what would be
// sent once /api/command is hooked up here.
const editPanel = document.getElementById("edit-panel");
const editToggle = document.getElementById("edit-toggle");
const editBody = document.querySelector("#edit-panel .edit-body");

const EDIT_PANEL_COLLAPSED_WIDTH = 44;
const EDIT_PANEL_EXPANDED_WIDTH = 320;

// reserve the collapsed strip's width in the canvas from the start (instant —
// there's nothing on screen yet to animate a transition from)
setRightPanelWidthInstant(EDIT_PANEL_COLLAPSED_WIDTH);

editToggle.addEventListener("click", () => {
	const expanded = editPanel.classList.toggle("expanded");
	editToggle.setAttribute("aria-expanded", String(expanded));
	setRightPanelWidth(expanded ? EDIT_PANEL_EXPANDED_WIDTH : EDIT_PANEL_COLLAPSED_WIDTH);
});

// "YYYY-MM-DDTHH:MM:SS..." (pydantic's JSON datetime) -> "YYYY-MM-DD" for <input type="date">
function isoToDateInputValue(iso) {
	return iso ? iso.slice(0, 10) : "";
}

// matches the CLI's `--depends_on 3,7` convention (comma-separated ids)
function idsToText(ids) {
	return (ids || []).join(",");
}

// field -> form element type, mirroring the README's `--field value` table
// (plus `name`, which the CLI exposes via `rename` rather than `update`)
const FIELD_DEFS = [
	{ key: "name", label: "Name", type: "text" },
	{ key: "description", label: "Description", type: "textarea" },
	{ key: "status", label: "Status", type: "text" },
	{ key: "priority", label: "Priority", type: "number" },
	{ key: "due_by", label: "Due by", type: "date", format: isoToDateInputValue },
	{ key: "completed", label: "Completed", type: "checkbox" },
	{ key: "dependency_ids", label: "Depends on", type: "text", format: idsToText },
];

// stub for now — will POST `update <id> --<field> <value>` to /api/command
// once that's wired up here
function handleFieldChange(item, def, value) {
	console.log(`(edit panel) would update item ${item.id}: --${def.key}`, value);
}

function buildField(item, def) {
	const wrapper = document.createElement("label");
	wrapper.className = "edit-field";

	const labelText = document.createElement("span");
	labelText.className = "edit-field-label";
	labelText.textContent = def.label;
	wrapper.appendChild(labelText);

	const rawValue = item[def.key];
	let input;

	if (def.type === "textarea") {
		input = document.createElement("textarea");
		input.value = rawValue || "";
		wrapper.appendChild(input);
	} else if (def.type === "checkbox") {
		const row = document.createElement("div");
		row.className = "edit-field-checkbox-row";
		input = document.createElement("input");
		input.type = "checkbox";
		input.checked = Boolean(rawValue);
		row.appendChild(input);
		wrapper.appendChild(row);
	} else {
		input = document.createElement("input");
		input.type = def.type; // "text", "number", or "date"
		input.value = def.format ? def.format(rawValue) : (rawValue ?? "");
		wrapper.appendChild(input);
	}

	input.addEventListener("change", () => {
		const value = def.type === "checkbox" ? input.checked : input.value;
		handleFieldChange(item, def, value);
	});

	return wrapper;
}

function renderEditForm(item) {
	editBody.innerHTML = "";

	if (!item) {
		const empty = document.createElement("div");
		empty.className = "edit-empty";
		empty.textContent = "Select a node to edit it.";
		editBody.appendChild(empty);
		return;
	}

	const form = document.createElement("div");
	form.className = "edit-form";
	FIELD_DEFS.forEach(def => form.appendChild(buildField(item, def)));
	editBody.appendChild(form);
}

// called by canvas.js whenever the selected node changes (click, or a tree
// refresh that re-resolves the current selection)
function onNodeSelected(item) {
	renderEditForm(item);
}

renderEditForm(null);
