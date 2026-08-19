// Collapsible console panel. Toggle + input echo only for now — real
// execution against /api/command lands once that endpoint exists.
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

consoleInput.addEventListener("keydown", (e) => {
	if (e.key !== "Enter") return;

	const command = consoleInput.value.trim();
	if (!command) return;

	appendLine("> " + command);
	consoleInput.value = "";
});
