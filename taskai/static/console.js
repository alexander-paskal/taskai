// Collapsible console panel. For now this just wires up the expand/collapse
// toggle — the scrollback + command input land once /api/command exists.
const consolePanel = document.getElementById("console-panel");
const consoleToggle = document.getElementById("console-toggle");

consoleToggle.addEventListener("click", () => {
	const expanded = consolePanel.classList.toggle("expanded");
	consoleToggle.setAttribute("aria-expanded", String(expanded));
});
