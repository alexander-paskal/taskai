// Global keyboard shortcuts + the left-hand reference panel that lists them.
// One registry (SHORTCUTS) drives both the key handler and the panel rows.
//
// Design rules (see the discussion in DEVLOG):
//   1. Shortcuts are inert while a text field is focused — the handler bails
//      out with no preventDefault, so arrows/letters behave normally when
//      typing. The only exceptions are marked `whileTyping`.
//   2. Only modifier-free keys and Shift+<key> are bound, with one deliberate
//      exception: Ctrl+Up/Down (into/out of a chain member's subtree). Nothing with Cmd/Alt or a
//      function key, so no OS/browser shortcut is shadowed (browser zoom
//      stays on Cmd/Ctrl +/-/0; we use bare +/-/0).
//   3. A shortcut never moves focus, except the two that are supposed to:
//      opening the terminal, and add-node (which focuses the name field).

const shortcutPanel = document.getElementById("shortcut-panel");
const shortcutToggle = document.getElementById("shortcut-toggle");
const shortcutBody = document.querySelector("#shortcut-panel .shortcut-body");

const SHORTCUT_PANEL_COLLAPSED_WIDTH = 44;
const SHORTCUT_PANEL_EXPANDED_WIDTH = 300;

// reserve the collapsed strip's width in the canvas from the start (instant)
state.camera.setPanelWidthInstant("left", SHORTCUT_PANEL_COLLAPSED_WIDTH);

function toggleShortcutPanel(force) {
	const expanded = typeof force === "boolean" ? force : !shortcutPanel.classList.contains("expanded");
	shortcutPanel.classList.toggle("expanded", expanded);
	shortcutToggle.setAttribute("aria-expanded", String(expanded));
	state.camera.setPanelWidth("left", expanded ? SHORTCUT_PANEL_EXPANDED_WIDTH : SHORTCUT_PANEL_COLLAPSED_WIDTH);
}

shortcutToggle.addEventListener("click", () => toggleShortcutPanel());

function toggleEditPanel() {
	if (editPanel.classList.contains("expanded")) closeEditPanelAndRefocus();
	else openEditPanel();
}

// close the edit panel, then ease the selected node back to center as the
// canvas widens out — without this the panel's width animation re-anchors on
// the old center and leaves the node cut off at the edge
function closeEditPanelAndRefocus() {
	closeEditPanel();
	const node = selectedRealNode();
	if (node) state.camera.focusOnNode(node);
}

// --- action helpers --------------------------------------------------------

// the selected node, or null when the selection is the synthetic root
// (i.e. "nothing / the whole tree")
function selectedRealNode() {
	return state.selectedNode && state.selectedNode !== state.graph.rootNode ? state.selectedNode : null;
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
	const item = state.graph.itemFor(node);
	runMutation(`${item && item.completed ? "undone" : "done"} ${node.id}`);
}

function deleteSelected() {
	const node = selectedRealNode();
	if (!node) return;
	runMutation(`delete ${node.id}`);
}

// add a child of the selected node (or a new root when nothing is selected),
// then select it, open the edit panel, and put the cursor in the name field
async function addNodeAndEdit() {
	const parent = selectedRealNode();
	const input = parent ? `add ${parent.id} "New task"` : `create "New task"`;

	const before = new Set(Object.keys(state.graph.itemsById));
	const data = await runMutation(input);
	if (!data) return;

	const newId = Object.keys(state.graph.itemsById).find(id => !before.has(id));
	const node = newId && state.graph.getNode(String(newId));
	if (!node) return;

	selectNode(node);
	// open the panel first so focusOnNode eases into the already-narrowing
	// canvas and its per-frame target tracks the new width (see focusOnNode)
	if (typeof openEditPanel === "function") openEditPanel();
	state.camera.focusOnNode(node);

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
	if (editPanel.classList.contains("expanded")) {
		closeEditPanelAndRefocus();
		return;
	}
	// nothing left to back out of (every panel collapsed): rehome the view
	if (![editPanel, consolePanel, shortcutPanel].some(p => p.classList.contains("expanded"))) {
		showAll();
		return;
	}
	// a panel is still open: just deselect, leaving the camera where it is
	selectNode(state.graph.rootNode);
}

// --- registry ------------------------------------------------------------

// the physical arrow -> structural direction mapping follows the layout's
// orientation (STYLE.layout.growthDown). By default the DAG grows downward
// and spreads sideways (graph.js's place()), so the key that feels like
// "descend"/"ascend" is Down/Up, and the one that steps across a depth
// level is Right/Left. Flipped (growing rightward), Right/Left descend/ascend
// and Down/Up step across a level.
const ARROW_DIR_GROWTH_RIGHT = { ArrowRight: "down", ArrowLeft: "up", ArrowDown: "right", ArrowUp: "left" };
const ARROW_DIR_GROWTH_DOWN = { ArrowDown: "down", ArrowUp: "up", ArrowRight: "right", ArrowLeft: "left" };
const arrowDir = (key) => (STYLE.layout.growthDown ? ARROW_DIR_GROWTH_DOWN : ARROW_DIR_GROWTH_RIGHT)[key];
// screen-space pan vectors, matching console.js's "pan <dir>" commands -
// tied to the actual screen direction, not tree semantics, so unaffected
// by the DAG's orientation
const PAN_VEC = { ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [1, 0], ArrowRight: [-1, 0] };

const SHORTCUTS = [
	{ section: "Panels" },
	{
		combos: [{ key: "`" }, { key: "~" }], glyphs: ["`"], desc: "Terminal (focus / close)",
		whileTyping: (el) => el === consoleInput, // also closes it from inside
		run: () => {
			if (document.activeElement === consoleInput) toggleConsole(false); // close from inside
			else if (consolePanel.classList.contains("expanded")) consoleInput.focus(); // open but unfocused -> jump in
			else toggleConsole(true); // closed -> open (focuses input)
		},
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
		combos: [{ key: "Escape" }], glyphs: ["Esc"], desc: "Leave field · close · show all",
		whileTyping: true, keepDefault: true,
		run: handleEscape,
	},

	{ section: "Move around" },
	{
		combos: [{ key: "ArrowUp" }, { key: "ArrowDown" }, { key: "ArrowLeft" }, { key: "ArrowRight" }],
		glyphs: ["↑", "↓", "←", "→"], desc: "Navigate the tree",
		run: (e) => navigate(arrowDir(e.key)),
	},
	{
		combos: [{ key: "ArrowUp", ctrl: true }, { key: "ArrowDown", ctrl: true }],
		glyphs: ["Ctrl↑", "Ctrl↓"], desc: "Into / out of a chain member's subtree",
		run: (e) => navigate(e.key === "ArrowDown" ? "into" : "out"),
	},
	{
		combos: [
			{ key: "ArrowUp", shift: true }, { key: "ArrowDown", shift: true },
			{ key: "ArrowLeft", shift: true }, { key: "ArrowRight", shift: true },
		],
		glyphs: ["⇧↑", "⇧↓", "⇧←", "⇧→"], desc: "Pan the view",
		run: (e) => { const [dx, dy] = PAN_VEC[e.key]; state.camera.pan(dx * PAN_AMOUNT, dy * PAN_AMOUNT); },
	},
	{
		combos: [{ key: "+" }, { key: "=" }], glyphs: ["+"], desc: "Zoom in",
		run: () => state.camera.zoom(ZOOM_FACTOR),
	},
	{
		combos: [{ key: "-" }], glyphs: ["–"], desc: "Zoom out",
		run: () => state.camera.zoom(1 / ZOOM_FACTOR),
	},
	{
		combos: [{ key: "0" }], glyphs: ["0"], desc: "Fit / show all",
		run: () => showAll(),
	},
	{
		combos: [{ key: "t" }], glyphs: ["t"], desc: "Flip layout direction",
		run: () => toggleOrientation(),
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
		combos: [{ key: "Delete" }], glyphs: ["Del"], desc: "Delete",
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
// character (a, +, ?, `) already carries Shift in e.key, so don't re-check it.
// Ctrl must match exactly (a combo without `ctrl` never fires with it held);
// Cmd/Alt never match anything
function comboMatches(combo, e) {
	if (e.metaKey || e.altKey || e.ctrlKey !== (combo.ctrl === true)) return false;
	if (combo.key.length > 1 && (combo.shift === true) !== e.shiftKey) return false;
	return combo.key === e.key;
}

window.addEventListener("keydown", (e) => {
	if (e.metaKey || e.altKey) return; // leave browser/OS combos alone (Ctrl combos are gated per-shortcut in comboMatches)

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
