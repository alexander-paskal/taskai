// Collapsible console panel: toggle, plus command submission against
// POST /api/command. That endpoint always returns the current full tree;
// `show` commands don't mutate anything, they just return a `focus` id
// telling us which node to center/zoom on.
const consolePanel = document.getElementById("console-panel");
const consoleToggle = document.getElementById("console-toggle");
const consoleInput = document.getElementById("console-input");
const consoleScrollback = document.getElementById("console-scrollback");

// `force` omitted = toggle; true/false = force that state. Opening focuses
// the command line so you can type straight away; closing blurs it so the
// keyboard-shortcut layer (which ignores keys while a field is focused)
// comes back to life.
function toggleConsole(force) {
	const expanded = typeof force === "boolean" ? force : !consolePanel.classList.contains("expanded");
	consolePanel.classList.toggle("expanded", expanded);
	consoleToggle.setAttribute("aria-expanded", String(expanded));
	if (expanded) consoleInput.focus();
	else consoleInput.blur();
}

consoleToggle.addEventListener("click", () => toggleConsole());

function appendLine(text) {
	const line = document.createElement("div");
	line.className = "console-line";
	line.textContent = text;
	consoleScrollback.appendChild(line);
	consoleScrollback.scrollTop = consoleScrollback.scrollHeight;
}

// raw filter args from the last `show <attr><op>value ...` query (e.g.
// `priority>3 status="IN PROGRESS"`), or null. Sent with every /api/command
// POST so a mutation's refreshed tree stays scoped to the same filtered view.
// Cleared by `show all` and by navigating to a specific node.
let activeFilter = null;

const PAN_AMOUNT = 250; // screen pixels per pan command
const ZOOM_FACTOR = 1.5;

const CLIENT_COMMANDS = {
	"zoom in":   () => state.camera.zoom(ZOOM_FACTOR),
	"zoom out":  () => state.camera.zoom(1 / ZOOM_FACTOR),
	"pan left":  () => state.camera.pan(PAN_AMOUNT, 0),
	"pan right": () => state.camera.pan(-PAN_AMOUNT, 0),
	"pan up":    () => state.camera.pan(0, PAN_AMOUNT),
	"pan down":  () => state.camera.pan(0, -PAN_AMOUNT),
	"up":        () => navigate("up"),
	"down":      () => navigate("down"),
	"left":      () => navigate("left"),
	"right":     () => navigate("right"),
	"forward":   () => navigate("forward"),
	"back":      () => navigate("back"),
	"hide edit": () => closeEditPanel(),
};

// `.` as a standalone token refers to the currently selected node — swap it
// for that node's id before the command is matched or sent on. Only matches a
// bare `.` (spaces or string ends on both sides), so `a.md` / `3.5` are left
// alone. Returns null (and reports) if `.` is used with no real selection.
function resolveDotRefs(command) {
	if (!/(^|\s)\.(\s|$)/.test(command)) return command;
	if (!state.selectedNode || state.selectedNode === state.graph.rootNode) {
		appendLine("No node selected — `.` refers to the selected node");
		return null;
	}
	return command.replace(/(^|\s)\.(?=\s|$)/g, `$1${state.selectedNode.id}`);
}

// POST a raw command string to the shared endpoint; returns the parsed
// { output, tree, focus } (or throws). Callers decide what to echo.
async function postCommand(input) {
	const body = { input };
	if (activeFilter) body.filter = activeFilter;
	const res = await fetch("/api/command", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
	return res.json();
}

// select the synthetic root and ease the view out to fit the whole forest —
// the `show` / `show all` console command and the keyboard shortcut share this
async function showAll() {
	try {
		await loadTree();
	} catch (err) {
		appendLine("Error: " + err.message);
		return;
	}
	activeFilter = null; // `show all` drops any filter
	selectNode(state.graph.rootNode);
	state.camera.fitAll(state.graph);
}

const commandHistory = [];
let historyIndex = commandHistory.length; // length = not currently browsing history

consoleInput.addEventListener("keydown", async (e) => {
	if (e.key === "ArrowUp") {
		if (historyIndex === 0) return;
		e.preventDefault();
		historyIndex--;
		consoleInput.value = commandHistory[historyIndex];
		return;
	}
	if (e.key === "ArrowDown") {
		if (historyIndex >= commandHistory.length) return;
		e.preventDefault();
		historyIndex++;
		consoleInput.value = historyIndex < commandHistory.length ? commandHistory[historyIndex] : "";
		return;
	}
	if (e.key !== "Enter") return;

	let command = consoleInput.value.trim();
	if (!command) return;

	commandHistory.push(command);
	historyIndex = commandHistory.length;

	appendLine("> " + command);
	consoleInput.value = "";

	command = resolveDotRefs(command); // `.` -> selected node's id
	if (command === null) return;

	const clientHandler = CLIENT_COMMANDS[command.toLowerCase()];
	if (clientHandler) {
		clientHandler();
		return;
	}

	// `show all` / bare `show` — select the synthetic root and fit the forest
	if (/^show(\s+all)?$/i.test(command)) {
		await showAll();
		return;
	}

	// `show <id|name>` — select + focus the resolved node. Does NOT open the
	// edit panel (that's `edit <id|name>`), mirroring click vs. double-click.
	const showMatch = command.match(/^show\s+(.+)$/i);
	if (showMatch) {
		const target = showMatch[1].trim();
		let data;
		try {
			data = await postCommand(command);
		} catch (err) {
			appendLine("Error: " + err.message);
			return;
		}

		applyTree(data.tree);

		// `show <attr><op><value> ...` — server returns a pruned tree + a flag
		if (data.filtered) {
			activeFilter = target; // remember it so mutations keep this view
			selectNode(state.graph.rootNode);
			state.camera.fitAll(state.graph);
			if (data.output) appendLine(data.output);
			return;
		}

		if (data.focus) {
			activeFilter = null; // navigated to a specific node — no longer filtered
			const node = state.graph.getNode(String(data.focus));
			if (node) {
				selectNode(node);
				state.camera.focusOnNode(node);
			}
		} else {
			appendLine(data.output || `No item found matching '${target}'`);
		}
		return;
	}

	// `edit <id|name>` — resolve via show, then select + focus + open panel
	const editMatch = command.match(/^edit\s+(.+)$/i);
	if (editMatch) {
		const target = editMatch[1].trim();
		let data;
		try {
			const res = await fetch("/api/command", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ input: `show ${target}` }),
			});
			data = await res.json();
		} catch (err) {
			appendLine("Error: " + err.message);
			return;
		}

		applyTree(data.tree);

		if (data.focus) {
			const node = state.graph.getNode(String(data.focus));
			if (node) {
				selectNode(node);
				state.camera.focusOnNode(node);
				if (typeof openEditPanel === "function") openEditPanel();
			}
		} else {
			appendLine(data.output || `No item found matching '${target}'`);
		}
		return;
	}

	let data;
	try {
		data = await postCommand(command);
	} catch (err) {
		appendLine("Error: " + err.message);
		return;
	}

	if (data.output) appendLine(data.output);

	applyTree(data.tree);

	if (data.focus) {
		const focusedNode = state.graph.getNode(String(data.focus));
		if (focusedNode) {
			selectNode(focusedNode);
			state.camera.focusOnNode(focusedNode);
		}
	}
});
