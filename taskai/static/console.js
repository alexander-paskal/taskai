// Collapsible console panel: toggle, plus command submission against
// POST /api/command. That endpoint always returns the current full tree;
// `show` commands don't mutate anything, they just return a `focus` id
// telling us which node to center/zoom on (see focusOnNode in canvas.js).
const consolePanel = document.getElementById("console-panel");
const consoleToggle = document.getElementById("console-toggle");
const consoleInput = document.getElementById("console-input");
const consoleScrollback = document.getElementById("console-scrollback");

consoleToggle.addEventListener("click", () => {
	const expanded = consolePanel.classList.toggle("expanded");
	consoleToggle.setAttribute("aria-expanded", String(expanded));
});

function appendLine(text) {
	const line = document.createElement("div");
	line.className = "console-line";
	line.textContent = text;
	consoleScrollback.appendChild(line);
	consoleScrollback.scrollTop = consoleScrollback.scrollHeight;
}

const PAN_AMOUNT = 250; // screen pixels per pan command
const ZOOM_FACTOR = 1.5;

const CLIENT_COMMANDS = {
	"zoom in":   () => canvasZoom(ZOOM_FACTOR),
	"zoom out":  () => canvasZoom(1 / ZOOM_FACTOR),
	"pan left":  () => canvasPan(PAN_AMOUNT, 0),
	"pan right": () => canvasPan(-PAN_AMOUNT, 0),
	"pan up":    () => canvasPan(0, PAN_AMOUNT),
	"pan down":  () => canvasPan(0, -PAN_AMOUNT),
};

consoleInput.addEventListener("keydown", async (e) => {
	if (e.key !== "Enter") return;

	const command = consoleInput.value.trim();
	if (!command) return;

	appendLine("> " + command);
	consoleInput.value = "";

	const clientHandler = CLIENT_COMMANDS[command.toLowerCase()];
	if (clientHandler) {
		clientHandler();
		return;
	}

	let data;
	try {
		const res = await fetch("/api/command", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ input: command }),
		});
		data = await res.json();
	} catch (err) {
		appendLine("Error: " + err.message);
		return;
	}

	if (data.output) appendLine(data.output);

	applyTree(data.tree);

	if (data.focus) {
		const focusedNode = nodes.find(n => n.id === String(data.focus));
		if (focusedNode) focusOnNode(focusedNode);
	}
});
