// Collapsible edit panel. Toggle only for now — the item form fields land
// once click-to-select exists on the DAG (see DEVPLAN Phase 1.4/1.5).
const editPanel = document.getElementById("edit-panel");
const editToggle = document.getElementById("edit-toggle");

const EDIT_PANEL_COLLAPSED_WIDTH = 44;
const EDIT_PANEL_EXPANDED_WIDTH = 320;

// reserve the collapsed strip's width in the canvas from the start
setRightPanelWidth(EDIT_PANEL_COLLAPSED_WIDTH);

editToggle.addEventListener("click", () => {
	const expanded = editPanel.classList.toggle("expanded");
	editToggle.setAttribute("aria-expanded", String(expanded));
	setRightPanelWidth(expanded ? EDIT_PANEL_EXPANDED_WIDTH : EDIT_PANEL_COLLAPSED_WIDTH);
});
