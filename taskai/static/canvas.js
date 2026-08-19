// Visual configuration for the DAG canvas. Plain data on purpose — this will
// eventually be served by a backend endpoint (e.g. GET /api/style) so the
// look can be themed/configured server-side instead of hardcoded here.
const STYLE = {
	colors: {
		background: "#f5f6f8",
		nodeFill: "#ffffff",
		nodeFillHover: "#f3f6ff",
		nodeBorder: "#e2e4ea",
		nodeBorderHover: "#4772fa",
		text: "#23252b",
		edge: "#dcdfe6",
		tooltipBackground: "#ffffff",
		tooltipBorder: "#e2e4ea",
		tooltipText: "#23252b",
	},
	node: {
		size: 160, // full square side length, in world units
		cornerRadius: 14,
		font: "20px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
		padding: 16,
		borderWidth: 1.5,
		borderWidthHover: 2,
		shadowColor: "rgba(15, 23, 42, 0.10)",
		shadowBlur: 10,
		shadowOffsetY: 2,
	},
	edge: {
		width: 1.25,
	},
	layout: {
		xSpacing: 230,
		ySpacing: 230,
		marginX: 120,
		marginY: 120,
		treeGap: 260, // extra horizontal gap, on top of xSpacing, between separate root trees
	},
	zoom: {
		min: 0.1,
		max: 4,
		speed: 0.001,
		focusScale: 1.4,
		focusDurationMs: 250,
	},
	tooltip: {
		font: "12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
		paddingX: 8,
		height: 24,
		cornerRadius: 6,
		offset: 10,
	},
};

let roots = [];
let nodes = [];

function flatten(node, list = []){
	list.push(node);
	node.children.forEach(child => flatten(child, list));
	return list;
}

// builds a renderable node tree from the flat {id: item} map returned by /api/tree
function buildTree(itemsById, id) {
	const item = itemsById[id];
	return {
		id: String(item.id),
		label: item.name,
		size: STYLE.node.size,
		children: (item.child_ids || []).map(childId => buildTree(itemsById, childId)),
	};
}

// depth-first layout: y from depth, x from a running leaf counter shared across the whole forest,
// with parent x centered over its children
function layout(node, depth, leafCounter) {
	node.y = STYLE.layout.marginY + depth * STYLE.layout.ySpacing;
	if (node.children.length === 0) {
		node.x = STYLE.layout.marginX + leafCounter.count * STYLE.layout.xSpacing;
		leafCounter.count += 1;
	} else {
		node.children.forEach(child => layout(child, depth + 1, leafCounter));
		const xs = node.children.map(c => c.x);
		node.x = (Math.min(...xs) + Math.max(...xs)) / 2;
	}
}

// builds the node tree + layout from a {id: item} map and (re)renders —
// shared by the initial /api/tree load and command responses from the
// console, which already carry the updated tree and don't need a refetch.
function applyTree(itemsById) {
	const rootIds = Object.values(itemsById)
		.filter(item => item.parent_id === null)
		.map(item => item.id);

	roots = rootIds.map(id => buildTree(itemsById, id));

	const leafCounter = { count: 0 };
	roots.forEach((root, i) => {
		if (i > 0) leafCounter.count += STYLE.layout.treeGap / STYLE.layout.xSpacing;
		layout(root, 0, leafCounter);
	});

	nodes = roots.flatMap(root => flatten(root));

	draw();
}

async function loadTree() {
	const res = await fetch("/api/tree");
	const itemsById = await res.json();
	applyTree(itemsById);
}

const canvas = document.getElementById("myCanvas");
const ctx = canvas.getContext("2d"); // get the canvas context I guess?

function resizeCanvas() {
	canvas.width = window.innerWidth;
	canvas.height = window.innerHeight;
	draw();
}
window.addEventListener("resize", resizeCanvas);

// pan/zoom view state: world coordinates map to screen as screen = world * scale + offset
const view = { offsetX: 0, offsetY: 0, scale: 1 };

function screenToWorld(sx, sy) {
	return { x: (sx - view.offsetX) / view.scale, y: (sy - view.offsetY) / view.scale };
}

function worldToScreen(wx, wy) {
	return { x: wx * view.scale + view.offsetX, y: wy * view.scale + view.offsetY };
}

// true if the world point (x, y) falls inside node's square
function hitTest(node, x, y) {
	const half = node.size / 2;
	return Math.abs(x - node.x) <= half && Math.abs(y - node.y) <= half;
}

// eases the view to center on `node` at `scale`
function focusOnNode(node, scale = STYLE.zoom.focusScale, duration = STYLE.zoom.focusDurationMs) {
	const startOffsetX = view.offsetX;
	const startOffsetY = view.offsetY;
	const startScale = view.scale;

	const targetOffsetX = canvas.width / 2 - node.x * scale;
	const targetOffsetY = canvas.height / 2 - node.y * scale;

	const startTime = performance.now();

	function step(now) {
		const t = Math.min(1, (now - startTime) / duration);
		const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic

		view.scale = startScale + (scale - startScale) * eased;
		view.offsetX = startOffsetX + (targetOffsetX - startOffsetX) * eased;
		view.offsetY = startOffsetY + (targetOffsetY - startOffsetY) * eased;

		draw();

		if (t < 1) requestAnimationFrame(step);
	}

	requestAnimationFrame(step);
}


// truncates text with an ellipsis until it fits maxWidth at the ctx's current font
function fitText(ctx, text, maxWidth) {
	if (ctx.measureText(text).width <= maxWidth) return text;
	let truncated = text;
	while (truncated.length > 0 && ctx.measureText(truncated + "…").width > maxWidth) {
		truncated = truncated.slice(0, -1);
	}
	return truncated ? truncated + "…" : "…";
}

function roundedRectPath(ctx, x, y, w, h, r) {
	ctx.beginPath();
	ctx.moveTo(x + r, y);
	ctx.arcTo(x + w, y, x + w, y + h, r);
	ctx.arcTo(x + w, y + h, x, y + h, r);
	ctx.arcTo(x, y + h, x, y, r);
	ctx.arcTo(x, y, x + w, y, r);
	ctx.closePath();
}

function draw() {
	ctx.fillStyle = STYLE.colors.background;
	ctx.fillRect(0, 0, canvas.width, canvas.height);

	ctx.save();
	ctx.translate(view.offsetX, view.offsetY);
	ctx.scale(view.scale, view.scale);

	// Draw connecting lines
	ctx.strokeStyle = STYLE.colors.edge;
	ctx.lineWidth = STYLE.edge.width;
	ctx.lineCap = "round";
	function drawLines(node) {
		node.children.forEach(child => {
			ctx.beginPath();
			ctx.moveTo(node.x, node.y);
			ctx.lineTo(child.x, child.y);
			ctx.stroke();
			drawLines(child);
		});
	}
	roots.forEach(root => drawLines(root));

	// Draw nodes
	nodes.forEach(node => {
		const half = node.size / 2;
		const isHovered = node === hoveredNode;
		const nodeX = node.x - half;
		const nodeY = node.y - half;

		ctx.save();
		ctx.shadowColor = STYLE.node.shadowColor;
		ctx.shadowBlur = STYLE.node.shadowBlur;
		ctx.shadowOffsetY = STYLE.node.shadowOffsetY;

		roundedRectPath(ctx, nodeX, nodeY, node.size, node.size, STYLE.node.cornerRadius);
		ctx.fillStyle = isHovered ? STYLE.colors.nodeFillHover : STYLE.colors.nodeFill;
		ctx.fill();
		ctx.restore(); // drop the shadow before stroking the border

		roundedRectPath(ctx, nodeX, nodeY, node.size, node.size, STYLE.node.cornerRadius);
		ctx.strokeStyle = isHovered ? STYLE.colors.nodeBorderHover : STYLE.colors.nodeBorder;
		ctx.lineWidth = isHovered ? STYLE.node.borderWidthHover : STYLE.node.borderWidth;
		ctx.stroke();

		ctx.fillStyle = STYLE.colors.text;
		ctx.font = STYLE.node.font;
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		const maxWidth = node.size - STYLE.node.padding * 2;
		ctx.fillText(fitText(ctx, node.label, maxWidth), node.x, node.y);
	});

	ctx.restore();

	// Full label tooltip for the hovered node, drawn in screen space (after restore)
	// so its text stays a fixed, readable size regardless of zoom level.
	if (hoveredNode) {
		const { x: sx, y: sy } = worldToScreen(hoveredNode.x, hoveredNode.y);
		const halfScreen = (hoveredNode.size / 2) * view.scale;

		ctx.font = STYLE.tooltip.font;
		const boxW = ctx.measureText(hoveredNode.label).width + STYLE.tooltip.paddingX * 2;
		const boxH = STYLE.tooltip.height;
		const boxX = sx - boxW / 2;
		const boxY = sy - halfScreen - boxH - STYLE.tooltip.offset;

		roundedRectPath(ctx, boxX, boxY, boxW, boxH, STYLE.tooltip.cornerRadius);
		ctx.fillStyle = STYLE.colors.tooltipBackground;
		ctx.fill();
		ctx.strokeStyle = STYLE.colors.tooltipBorder;
		ctx.lineWidth = 1;
		ctx.stroke();

		ctx.fillStyle = STYLE.colors.tooltipText;
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		ctx.fillText(hoveredNode.label, sx, boxY + boxH / 2);
	}
}

// hovering color change
let hoveredNode = null;

// panning state
let isPanning = false;
let didPan = false; // set once a mousedown->mousemove drag moves enough to count as a pan, not a click
let panStart = null; // {x, y, offsetX, offsetY} in screen coords

canvas.addEventListener("click", (e) => {
	if (didPan) {
		didPan = false;
		return;
	}

	const rect = canvas.getBoundingClientRect();
	const { x, y } = screenToWorld(e.clientX - rect.left, e.clientY - rect.top);

	const clicked = nodes.find(node => hitTest(node, x, y));

	if (clicked) {
		console.log("Clicked:", clicked.id, clicked.label);
	}
})

canvas.addEventListener("dblclick", (e) => {
	const rect = canvas.getBoundingClientRect();
	const { x, y } = screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
	const clicked = nodes.find(node => hitTest(node, x, y));

	if (clicked) {
		focusOnNode(clicked);
	}
})

canvas.addEventListener("mousedown", (e) => {
	const rect = canvas.getBoundingClientRect();
	isPanning = true;
	didPan = false;
	panStart = {
		x: e.clientX - rect.left,
		y: e.clientY - rect.top,
		offsetX: view.offsetX,
		offsetY: view.offsetY,
	};
	canvas.style.cursor = "grabbing";
})

window.addEventListener("mouseup", () => {
	isPanning = false;
	canvas.style.cursor = hoveredNode ? "pointer" : "default";
})

canvas.addEventListener("mousemove", (e) => {
	const rect = canvas.getBoundingClientRect();
	const sx = e.clientX - rect.left;
	const sy = e.clientY - rect.top;

	if (isPanning) {
		const dx = sx - panStart.x;
		const dy = sy - panStart.y;
		if (Math.abs(dx) > 3 || Math.abs(dy) > 3) didPan = true;
		view.offsetX = panStart.offsetX + dx;
		view.offsetY = panStart.offsetY + dy;
		draw();
		return;
	}

	const { x, y } = screenToWorld(sx, sy);
	const found = nodes.find(n => hitTest(n, x, y));

	if (found !== hoveredNode) {
		hoveredNode = found || null;
		canvas.style.cursor = found ? "pointer": "default";
		draw();
	}
})

// zoom, keeping the point under the cursor fixed on screen
canvas.addEventListener("wheel", (e) => {
	e.preventDefault();

	const rect = canvas.getBoundingClientRect();
	const sx = e.clientX - rect.left;
	const sy = e.clientY - rect.top;

	const worldBefore = screenToWorld(sx, sy);
	const zoomFactor = Math.exp(-e.deltaY * STYLE.zoom.speed);
	view.scale = Math.min(STYLE.zoom.max, Math.max(STYLE.zoom.min, view.scale * zoomFactor));
	view.offsetX = sx - worldBefore.x * view.scale;
	view.offsetY = sy - worldBefore.y * view.scale;

	draw();
}, { passive: false })


resizeCanvas();
loadTree();
