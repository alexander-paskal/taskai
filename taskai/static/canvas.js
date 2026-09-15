// High-level wiring: builds a Graph from /api/tree, drives a Camera over
// it, and turns raw DOM events into navigation/selection/render calls.
// `state` is the single source of truth the other panel scripts read from
// and act through.

const canvasEl = document.getElementById("myCanvas");
const ctx = canvasEl.getContext("2d");

const state = {
	graph: new Graph({}),
	camera: null,
	selectedNode: null,
	previousSelectedId: null, // one level of "where was I before this" - see selectNode
	hoveredNode: null,
};
state.camera = new Camera(canvasEl, redraw);
state.selectedNode = state.graph.rootNode;

function redraw() {
	render(ctx, state.camera, state.graph, state.selectedNode, state.hoveredNode);
}

// selection persists across hover and drives the edit panel (see
// onNodeSelected, defined in editpanel.js). Remembers the prior selection
// (by id, not reference - nodes are rebuilt on every tree refresh) so that
// if the current selection later disappears (e.g. it gets deleted),
// applyTree can fall back to it instead of jumping straight to the root.
function selectNode(node) {
	if (state.selectedNode && state.selectedNode.id !== node.id) {
		state.previousSelectedId = state.selectedNode.id;
	}
	state.selectedNode = node;
	if (typeof onNodeSelected === "function") onNodeSelected(state.graph.itemFor(node));
	redraw();
}

// rebuilds the graph from a {id: item} map and redraws — shared by the
// initial /api/tree load and command responses from the console, which
// already carry the updated tree and don't need a refetch
function applyTree(itemsById) {
	state.graph = new Graph(itemsById);

	// the previous selection is now a stale object (nodes are rebuilt every
	// time) - re-resolve it by id so selection survives a tree refresh. If
	// it's gone (e.g. just deleted), fall back to the previously-selected
	// node before it, and only give up to the synthetic root if that's gone too.
	const prevId = state.selectedNode ? state.selectedNode.id : null;
	const resolved = (prevId && state.graph.getNode(prevId))
		|| (state.previousSelectedId && state.graph.getNode(state.previousSelectedId))
		|| state.graph.rootNode;
	selectNode(resolved);
}

async function loadTree() {
	const res = await fetch("/api/tree");
	applyTree(await res.json());
}

// raw CLIConfig from the server, stashed on STYLE so any renderer-relevant
// key (e.g. status colors) can be added there and read here with no new
// endpoint or fetch needed. Config.js seeds STYLE.serverConfig = {} so
// consumers can safely read from it even before this resolves.
async function loadConfig() {
	try {
		const res = await fetch("/api/style");
		STYLE.serverConfig = await res.json();
	} catch (err) {
		console.error("Failed to load server config, using defaults:", err);
	}
}

function navigate(direction) {
	const target = navigateGraph(direction, state.selectedNode || state.graph.rootNode, state.graph);
	if (!target) return;

	selectNode(target);
	if (target === state.graph.rootNode) state.camera.fitAll(state.graph);
	else state.camera.focusOnNode(target);
}

window.addEventListener("resize", () => state.camera.resize());

let isPanning = false;
let didPan = false; // set once a mousedown->mousemove drag moves enough to count as a pan, not a click
let panStart = null; // {x, y, offsetX, offsetY} in screen coords

canvasEl.addEventListener("click", (e) => {
	if (didPan) {
		didPan = false;
		return;
	}
	const rect = canvasEl.getBoundingClientRect();
	const { x, y } = state.camera.screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
	selectNode(state.graph.hitTest(x, y) || state.graph.rootNode); // empty canvas -> whole-tree selection
});

canvasEl.addEventListener("dblclick", (e) => {
	const rect = canvasEl.getBoundingClientRect();
	const { x, y } = state.camera.screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
	const clicked = state.graph.hitTest(x, y);
	if (!clicked) return;

	selectNode(clicked); // single click already selected it; double click also opens the editor
	if (typeof openEditPanel === "function") openEditPanel();
	state.camera.focusOnNode(clicked); // after openEditPanel so the ease tracks the narrowed canvas
});

canvasEl.addEventListener("mousedown", (e) => {
	const rect = canvasEl.getBoundingClientRect();
	isPanning = true;
	didPan = false;
	panStart = {
		x: e.clientX - rect.left,
		y: e.clientY - rect.top,
		offsetX: state.camera.offsetX,
		offsetY: state.camera.offsetY,
	};
	canvasEl.style.cursor = "grabbing";
});

window.addEventListener("mouseup", () => {
	isPanning = false;
	canvasEl.style.cursor = state.hoveredNode ? "pointer" : "default";
});

canvasEl.addEventListener("mousemove", (e) => {
	const rect = canvasEl.getBoundingClientRect();
	const sx = e.clientX - rect.left;
	const sy = e.clientY - rect.top;

	if (isPanning) {
		const dx = sx - panStart.x;
		const dy = sy - panStart.y;
		if (Math.abs(dx) > 3 || Math.abs(dy) > 3) didPan = true;
		state.camera.offsetX = panStart.offsetX + dx;
		state.camera.offsetY = panStart.offsetY + dy;
		redraw();
		return;
	}

	const { x, y } = state.camera.screenToWorld(sx, sy);
	const found = state.graph.hitTest(x, y);
	if (found !== state.hoveredNode) {
		state.hoveredNode = found;
		canvasEl.style.cursor = found ? "pointer" : "default";
		redraw();
	}
});

// zoom, keeping the point under the cursor fixed on screen
canvasEl.addEventListener("wheel", (e) => {
	e.preventDefault();
	const rect = canvasEl.getBoundingClientRect();
	const zoomFactor = Math.exp(-e.deltaY * STYLE.zoom.speed);
	state.camera.zoomAtPoint(e.clientX - rect.left, e.clientY - rect.top, zoomFactor);
}, { passive: false });

state.camera.resize();
loadConfig().then(loadTree);

// refetch on window focus so edits made elsewhere (e.g. the CLI) while this
// tab was in the background show up without needing a manual reload
window.addEventListener("focus", loadTree);
