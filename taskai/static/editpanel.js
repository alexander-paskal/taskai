// Collapsible edit panel. Click a node on the DAG (see canvas.js's click
// handler, which calls onNodeSelected below) to populate this form with its
// data. Field edits POST `update <id> --<field> <value>` to /api/command,
// the same endpoint and command grammar the console uses.
const editPanel = document.getElementById("edit-panel");
const editToggle = document.getElementById("edit-toggle");
const editBody = document.querySelector("#edit-panel .edit-body");

const EDIT_PANEL_COLLAPSED_WIDTH = 44;
const EDIT_PANEL_EXPANDED_WIDTH = 448;

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

// "YYYY-MM-DD" (native <input type="date"> value) -> "MM-DD-YYYY", matching
// the CLI's documented --due_by format
function dateInputValueToCliFormat(value) {
	const [year, month, day] = value.split("-");
	return `${month}-${day}-${year}`;
}

// field -> form element type, mirroring the README's `--field value` table
// (plus `name`, which the CLI exposes via `rename` rather than `update`).
// `param` overrides the CLI flag name where it differs from the JSON key.
const FIELD_DEFS = [
	{ key: "name", label: "Name", type: "text" },
	{ key: "status", label: "Status", type: "text" },
	{ key: "priority", label: "Priority", type: "number" },
	{ key: "due_by", label: "Due by", type: "date", format: isoToDateInputValue },
	{ key: "completed", label: "Completed", type: "checkbox" },
	// description goes last and is flagged `grow`: it's the big free-text
	// field, so it sits at the bottom and stretches to fill whatever panel
	// height is left (see .edit-field-grow in style.css)
	{ key: "description", label: "Description", type: "textarea", grow: true },
];

// debounce field updates so we're not POSTing on every keystroke — only
// once input goes quiet for a bit. Checkboxes bypass this: a toggle is
// already a single, complete action, not something to wait out.
const FIELD_UPDATE_DEBOUNCE_MS = 1000;
const pendingFieldUpdates = {};

// _parse_arg_string (cli.py) has no escape mechanism, so swap embedded
// double quotes rather than let them break the command's tokenization
function quoteArg(value) {
	return `"${String(value).replace(/"/g, "'")}"`;
}

async function sendFieldUpdate(item, def, value) {
	const field = def.param || def.key;
	const command = `update ${item.id} --${field} ${quoteArg(value)}`;

	let data;
	try {
		const res = await fetch("/api/command", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ input: command }),
		});
		data = await res.json();
	} catch (err) {
		appendLine(`Error updating item ${item.id}: ${err.message}`);
		return;
	}

	if (data.output) appendLine(data.output);
	applyTree(data.tree);
}

// adds a comment via the same command pipeline as everything else —
// `comment <id> "<text>"`. The returned tree carries the new comment (see
// _resolve_comments in browser.py), so applyTree refreshes the list.
async function sendComment(itemId, text) {
	const command = `comment ${itemId} ${quoteArg(text)}`;

	let data;
	try {
		const res = await fetch("/api/command", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ input: command }),
		});
		data = await res.json();
	} catch (err) {
		appendLine(`Error adding comment to item ${itemId}: ${err.message}`);
		return;
	}

	if (data.output) appendLine(data.output);
	applyTree(data.tree);
}

function handleFieldChange(item, def, value) {
	if (def.type === "checkbox") {
		sendFieldUpdate(item, def, value ? "true" : "false");
		return;
	}

	if (def.key === "due_by") {
		if (!value) return; // clearing due_by isn't supported by the CLI today
		value = dateInputValueToCliFormat(value);
	}

	const timerKey = `${item.id}:${def.key}`;
	clearTimeout(pendingFieldUpdates[timerKey]);
	pendingFieldUpdates[timerKey] = setTimeout(() => {
		delete pendingFieldUpdates[timerKey];
		sendFieldUpdate(item, def, value);
	}, FIELD_UPDATE_DEBOUNCE_MS);
}

// the value to show in a field's input for the given item — checkbox uses
// the boolean directly (assigned to .checked), the rest get a string .value
function fieldDisplayValue(item, def) {
	const raw = item[def.key];
	if (def.type === "checkbox") return Boolean(raw);
	if (def.type === "textarea") return raw || "";
	if (def.format) return def.format(raw);
	return raw ?? "";
}

function buildField(item, def) {
	const wrapper = document.createElement("label");
	wrapper.className = "edit-field";
	if (def.grow) wrapper.classList.add("edit-field-grow");

	const labelText = document.createElement("span");
	labelText.className = "edit-field-label";
	labelText.textContent = def.label;
	wrapper.appendChild(labelText);

	let input;

	if (def.type === "textarea") {
		input = document.createElement("textarea");
		input.value = fieldDisplayValue(item, def);
		wrapper.appendChild(input);
	} else if (def.type === "checkbox") {
		const row = document.createElement("div");
		row.className = "edit-field-checkbox-row";
		input = document.createElement("input");
		input.type = "checkbox";
		input.checked = fieldDisplayValue(item, def);
		row.appendChild(input);
		wrapper.appendChild(row);
	} else {
		input = document.createElement("input");
		input.type = def.type; // "text", "number", or "date"
		input.value = fieldDisplayValue(item, def);
		wrapper.appendChild(input);
	}

	input.dataset.fieldKey = def.key; // for the in-place refresh in renderEditForm

	// checkboxes are a single discrete action (send immediately); everything
	// else listens on "input" so the debounce in handleFieldChange can wait
	// out a pause in typing rather than requiring the field to lose focus
	const eventName = def.type === "checkbox" ? "change" : "input";
	input.addEventListener(eventName, () => {
		const value = def.type === "checkbox" ? input.checked : input.value;
		handleFieldChange(item, def, value);
	});

	return wrapper;
}

// "YYYY-MM-DDTHH:MM:SS..." -> "Sep 3, 2026"; empty string if unparseable
function formatCommentDate(iso) {
	if (!iso) return "";
	const d = new Date(iso);
	if (isNaN(d.getTime())) return "";
	return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

// (re)fill a <ul.comment-list> from an item's resolved `comments` array.
// Oldest first, newest at the bottom; keeps the view pinned to the bottom
// (newest) unless the user has deliberately scrolled up into the history.
function renderCommentList(listEl, comments) {
	const prevScrollTop = listEl.scrollTop;
	const stickToBottom =
		listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight < 8;

	listEl.innerHTML = "";

	if (!comments || !comments.length) {
		const empty = document.createElement("li");
		empty.className = "comment-empty";
		empty.textContent = "No comments yet.";
		listEl.appendChild(empty);
		return;
	}

	comments.forEach(c => {
		const li = document.createElement("li");
		li.className = "comment-item";

		// date first so it lands on the left; body second, right-aligned
		const when = formatCommentDate(c.created_on);
		if (when) {
			const time = document.createElement("time");
			time.className = "comment-date";
			time.textContent = when;
			li.appendChild(time);
		}

		const body = document.createElement("span");
		body.className = "comment-body";
		body.textContent = c.content;
		li.appendChild(body);

		listEl.appendChild(li);
	});

	// defer to next frame so scrollHeight is valid even on the first render
	// (the <ul> isn't laid out yet when buildCommentsSection calls this)
	if (stickToBottom) {
		requestAnimationFrame(() => { listEl.scrollTop = listEl.scrollHeight; });
	} else {
		listEl.scrollTop = prevScrollTop; // keep the reader where they were
	}
}

// read-only comment list + an "add" input, styled like an .edit-field
function buildCommentsSection(item) {
	const section = document.createElement("div");
	section.className = "edit-field edit-comments";

	const label = document.createElement("span");
	label.className = "edit-field-label";
	label.textContent = "Comments";
	section.appendChild(label);

	const list = document.createElement("ul");
	list.className = "comment-list";
	renderCommentList(list, item.comments);
	section.appendChild(list);

	const addInput = document.createElement("textarea");
	addInput.className = "comment-add-input";
	addInput.rows = 2;
	addInput.placeholder = "Add a comment…";
	// Enter sends, Shift+Enter inserts a newline
	addInput.addEventListener("keydown", e => {
		if (e.key !== "Enter" || e.shiftKey) return;
		e.preventDefault();
		const text = addInput.value.trim();
		if (!text) return;
		addInput.value = "";
		sendComment(item.id, text);
	});
	section.appendChild(addInput);

	return section;
}

// id of the item the form is currently showing, so a same-item refresh
// (e.g. the applyTree after our own debounced field POST) can update values
// in place instead of tearing the form down and unfocusing the live field
let renderedItemId = null;

// push fresh values into the existing inputs without rebuilding them — skips
// whichever field the user is currently editing so we don't stomp their input
function refreshFieldValues(item) {
	editBody.querySelectorAll("[data-field-key]").forEach(input => {
		if (input === document.activeElement) return;
		const def = FIELD_DEFS.find(d => d.key === input.dataset.fieldKey);
		if (!def) return;
		if (def.type === "checkbox") input.checked = fieldDisplayValue(item, def);
		else input.value = fieldDisplayValue(item, def);
	});
}

function renderEditForm(item) {
	if (item && String(item.id) === renderedItemId && editBody.querySelector(".edit-form")) {
		refreshFieldValues(item);
		const list = editBody.querySelector(".comment-list");
		if (list) renderCommentList(list, item.comments);
		return;
	}

	renderedItemId = item ? String(item.id) : null;
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
	form.appendChild(buildCommentsSection(item)); // comment feed at the bottom
	editBody.appendChild(form);
}

// called by canvas.js whenever the selected node changes (click, or a tree
// refresh that re-resolves the current selection)
function onNodeSelected(item) {
	renderEditForm(item);
}

// expands the edit panel if it isn't already — called by the console's
// `edit <node>` / `edit .` commands so the panel opens without a click
function openEditPanel() {
	if (!editPanel.classList.contains("expanded")) {
		editPanel.classList.add("expanded");
		editToggle.setAttribute("aria-expanded", "true");
		setRightPanelWidth(EDIT_PANEL_EXPANDED_WIDTH);
	}
}

// collapses the edit panel if it's open — the `hide edit` console command
function closeEditPanel() {
	if (editPanel.classList.contains("expanded")) {
		editPanel.classList.remove("expanded");
		editToggle.setAttribute("aria-expanded", "false");
		setRightPanelWidth(EDIT_PANEL_COLLAPSED_WIDTH);
	}
}

renderEditForm(null);
