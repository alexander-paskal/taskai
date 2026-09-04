// Global keyboard shortcuts + the left-hand reference panel that lists them.
// One registry (SHORTCUTS) drives both the key handler and the panel rows.
//
// Design rules (see the discussion in DEVLOG):
//   1. Shortcuts are inert while a text field is focused — the handler bails
//      out with no preventDefault, so arrows/letters behave normally when
//      typing. The only exceptions are marked `whileTyping`.
//   2. Only modifier-free keys and Shift+<key> are bound. Nothing with
//      Ctrl/Cmd/Alt or a function key, so no OS/browser shortcut is shadowed
//      (browser zoom stays on Cmd/Ctrl +/-/0; we use bare +/-/0).
//   3. A shortcut never moves focus, except the two that are supposed to:
//      opening the terminal, and add-node (which focuses the name field).

const shortcutPanel = document.getElementById("shortcut-panel");
const shortcutToggle = document.getElementById("shortcut-toggle");
const shortcutBody = document.querySelector("#shortcut-panel .shortcut-body");

const SHORTCUT_PANEL_COLLAPSED_WIDTH = 44;
const SHORTCUT_PANEL_EXPANDED_WIDTH = 300;

// reserve the collapsed strip's width in the canvas from the start (instant)
setPanelWidthInstant("left", SHORTCUT_PANEL_COLLAPSED_WIDTH);

function toggleShortcutPanel(force) {
	const expanded = typeof force === "boolean" ? force : !shortcutPanel.classList.contains("expanded");
	shortcutPanel.classList.toggle("expanded", expanded);
	shortcutToggle.setAttribute("aria-expanded", String(expanded));
	setPanelWidth("left", expanded ? SHORTCUT_PANEL_EXPANDED_WIDTH : SHORTCUT_PANEL_COLLAPSED_WIDTH);
}

shortcutToggle.addEventListener("click", () => toggleShortcutPanel());

function toggleEditPanel() {
	if (editPanel.classList.contains("expanded")) closeEditPanel();
	else openEditPanel();
}

// --- action helpers --------------------------------------------------------

// the selected node, or null when the selection is the synthetic root
// (i.e. "nothing / the whole tree")
function selectedRealNode() {
	return selectedNode && selectedNode !== rootNode ? selectedNode : null;
}

// run a DB-mutating command through the shared endpoint. No `> echo` (that's
// for things the user typed), but we do surface `output` since the command
// changed the database — matching "not visible unless it modifies the DB".
async function runMutation(input) {
	let data;
	try {
		data = await postCommand(input);
	} catch (err) {
		appendLine("Error: " + err.message);
		return null;
	}
	if (data.output) appendLine(data.output.trim());
	applyTree(data.tree);
	return data;
}

function toggleDoneSelected() {
	const node = selectedRealNode();
	if (!node) return;
	const item = itemForNode(node);
	runMutation(`${item && item.completed ? "undone" : "done"} ${node.id}`);
}

function deleteSelected() {
	const node = selectedRealNode();
	if (!node) return;
	const item = itemForNode(node);
	const label = item ? item.name : node.id;
	if (!window.confirm(`Delete "${label}" and everything under it?`)) return;
	runMutation(`delete ${node.id}`);
}

// add a child of the selected node (or a new root when nothing is selected),
// then select it, open the edit panel, and put the cursor in the name field
async function addNodeAndEdit() {
	const parent = selectedRealNode();
	const input = parent ? `add ${parent.id} "New task"` : `create "New task"`;

	const before = new Set(Object.keys(latestItemsById));
	const data = await runMutation(input);
	if (!data) return;

	const newId = Object.keys(latestItemsById).find(id => !before.has(id));
	const node = newId && nodes.find(n => n.id === String(newId));
	if (!node) return;

	selectedNode = node;
	if (typeof onNodeSelected === "function") onNodeSelected(itemForNode(node));
	focusOnNode(node);
	if (typeof openEditPanel === "function") openEditPanel();

	requestAnimationFrame(() => {
		const nameInput = document.querySelector('#edit-panel [data-field-key="name"]');
		if (nameInput) {
			nameInput.focus();
			nameInput.select();
		}
	});
}

function handleEscape() {
	const el = document.activeElement;
	if (el === consoleInput) {
		toggleConsole(false);
		return;
	}
	if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) {
		el.blur();
		return;
	}
	showAll(); // deselects (selectedNode = rootNode) and fits the whole forest
}

// --- registry ------------------------------------------------------------

const ARROW_DIR = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
// screen-space pan vectors, matching console.js's "pan <dir>" commands
const PAN_VEC = { ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [1, 0], ArrowRight: [-1, 0] };

const SHORTCUTS = [
	{ section: "Panels" },
	{
		combos: [{ key: "`" }], glyphs: ["`"], desc: "Toggle terminal",
		whileTyping: (el) => el === consoleInput, // also closes it from inside
		run: () => toggleConsole(),
	},
	{
		combos: [{ key: "?" }], glyphs: ["?"], desc: "Toggle this panel",
		run: () => toggleShortcutPanel(),
	},
	{
		combos: [{ key: "e" }], glyphs: ["e"], desc: "Toggle edit panel",
		run: () => toggleEditPanel(),
	},
	{
		combos: [{ key: "Escape" }], glyphs: ["Esc"], desc: "Leave field · deselect · show all",
		whileTyping: true, keepDefault: true,
		run: handleEscape,
	},

	{ section: "Move around" },
	{
		combos: [{ key: "ArrowUp" }, { key: "ArrowDown" }, { key: "ArrowLeft" }, { key: "ArrowRight" }],
		glyphs: ["↑", "↓", "←", "→"], desc: "Navigate the tree",
		run: (e) => navigate(ARROW_DIR[e.key]),
	},
	{
		combos: [
			{ key: "ArrowUp", shift: true }, { key: "ArrowDown", shift: true },
			{ key: "ArrowLeft", shift: true }, { key: "ArrowRight", shift: true },
		],
		glyphs: ["⇧↑", "⇧↓", "⇧←", "⇧→"], desc: "Pan the view",
		run: (e) => { const [dx, dy] = PAN_VEC[e.key]; canvasPan(dx * PAN_AMOUNT, dy * PAN_AMOUNT); },
	},
	{
		combos: [{ key: "+" }, { key: "=" }], glyphs: ["+"], desc: "Zoom in",
		run: () => canvasZoom(ZOOM_FACTOR),
	},
	{
		combos: [{ key: "-" }], glyphs: ["–"], desc: "Zoom out",
		run: () => canvasZoom(1 / ZOOM_FACTOR),
	},
	{
		combos: [{ key: "0" }], glyphs: ["0"], desc: "Fit / show all",
		run: () => showAll(),
	},

	{ section: "Selected node" },
	{
		combos: [{ key: "a" }], glyphs: ["a"], desc: "Add a child, edit its name",
		run: () => addNodeAndEdit(),
	},
	{
		combos: [{ key: "d" }], glyphs: ["d"], desc: "Toggle done",
		run: () => toggleDoneSelected(),
	},
	{
		combos: [{ key: "Delete" }], glyphs: ["Del"], desc: "Delete (asks first)",
		run: () => deleteSelected(),
	},
];

// --- key handling --------------------------------------------------------

function isTypingContext() {
	const el = document.activeElement;
	if (!el) return false;
	return el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable;
}

// a named key (ArrowUp, Delete, Escape) can be gated on Shift; a typed
// character (a, +, ?, `) already carries Shift in e.key, so don't re-check it
function comboMatches(combo, e) {
	if (e.ctrlKey || e.metaKey || e.altKey) return false;
	if (combo.key.length > 1 && (combo.shift === true) !== e.shiftKey) return false;
	return combo.key === e.key;
}

window.addEventListener("keydown", (e) => {
	if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser/OS combos alone

	const typing = isTypingContext();

	for (const sc of SHORTCUTS) {
		if (!sc.combos) continue;

		const wt = typeof sc.whileTyping === "function"
			? sc.whileTyping(document.activeElement)
			: !!sc.whileTyping;
		if (typing && !wt) continue;

		if (!sc.combos.some(c => comboMatches(c, e))) continue;

		if (!sc.keepDefault) e.preventDefault();
		sc.run(e);
		return;
	}
});

// --- panel rendering ---------------------------------------------------

function renderShortcutList() {
	shortcutBody.innerHTML = "";

	const list = document.createElement("div");
	list.className = "shortcut-list";

	SHORTCUTS.forEach(sc => {
		if (sc.section) {
			const h = document.createElement("div");
			h.className = "shortcut-section";
			h.textContent = sc.section;
			list.appendChild(h);
			return;
		}

		const row = document.createElement("div");
		row.className = "shortcut-row";

		const keys = document.createElement("div");
		keys.className = "shortcut-keys";
		sc.glyphs.forEach(g => {
			const k = document.createElement("span");
			k.className = "shortcut-key";
			k.textContent = g;
			keys.appendChild(k);
		});
		row.appendChild(keys);

		const desc = document.createElement("div");
		desc.className = "shortcut-desc";
		desc.textContent = sc.desc;
		row.appendChild(desc);

		list.appendChild(row);
	});

	shortcutBody.appendChild(list);
}

renderShortcutList();
