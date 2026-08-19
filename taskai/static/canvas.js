// const canvas = document.getElementById('myCanvas');
// const ctx = canvas.getContext('2d');

// canvas.width = 400;
// canvas.height = 300;

// ctx.fillStyle = 'tomato';
// ctx.fillRect(20, 20, 100, 80);


const NODE_RADIUS = 25;
const X_SPACING = 90;
const Y_SPACING = 100;
const MARGIN_X = 60;
const MARGIN_Y = 60;

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
		r: NODE_RADIUS,
		children: (item.child_ids || []).map(childId => buildTree(itemsById, childId)),
	};
}

// depth-first layout: y from depth, x from a running leaf counter shared across the whole forest,
// with parent x centered over its children
function layout(node, depth, leafCounter) {
	node.y = MARGIN_Y + depth * Y_SPACING;
	if (node.children.length === 0) {
		node.x = MARGIN_X + leafCounter.count * X_SPACING;
		leafCounter.count += 1;
	} else {
		node.children.forEach(child => layout(child, depth + 1, leafCounter));
		const xs = node.children.map(c => c.x);
		node.x = (Math.min(...xs) + Math.max(...xs)) / 2;
	}
}

async function loadTree() {
	const res = await fetch("/api/tree");
	const itemsById = await res.json();

	const rootIds = Object.values(itemsById)
		.filter(item => item.parent_id === null)
		.map(item => item.id);

	roots = rootIds.map(id => buildTree(itemsById, id));

	const leafCounter = { count: 0 };
	roots.forEach(root => layout(root, 0, leafCounter));

	nodes = roots.flatMap(root => flatten(root));

	draw();
}

const canvas = document.getElementById("myCanvas");
const ctx = canvas.getContext("2d"); // get the canvas context I guess?

canvas.width = 800;
canvas.height = 800;

// pan/zoom view state: world coordinates map to screen as screen = world * scale + offset
const view = { offsetX: 0, offsetY: 0, scale: 1 };
const MIN_SCALE = 0.2;
const MAX_SCALE = 4;
const ZOOM_SPEED = 0.001;
const FOCUS_SCALE = 2;
const FOCUS_DURATION_MS = 250;

function screenToWorld(sx, sy) {
	return { x: (sx - view.offsetX) / view.scale, y: (sy - view.offsetY) / view.scale };
}

function worldToScreen(wx, wy) {
	return { x: wx * view.scale + view.offsetX, y: wy * view.scale + view.offsetY };
}

// eases the view to center on `node` at `scale`
function focusOnNode(node, scale = FOCUS_SCALE, duration = FOCUS_DURATION_MS) {
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

function draw() {
	ctx.clearRect(0, 0, canvas.width, canvas.height);

	ctx.save();
	ctx.translate(view.offsetX, view.offsetY);
	ctx.scale(view.scale, view.scale);

	// Draw connecting Lines
	function drawLines(node) {
		node.children.forEach(child => {
			ctx.beginPath();
			ctx.moveTo(node.x, node.y);
			ctx.lineTo(child.x, child.y);
			ctx.strokeStyle = "#999";
			ctx.stroke();
			drawLines(child);
		});
	}
	roots.forEach(root => drawLines(root));

	// Draw circles
	nodes.forEach(node => {
		ctx.beginPath();
		ctx.arc(node.x,node.y,node.r,0, Math.PI*2);
		ctx.fillStyle = node === hoveredNode ? "#3f6d97" : "steelblue";
		ctx.fill();

		ctx.fillStyle = "white";
		ctx.font = "10px sans-serif";
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		const maxWidth = node.r * 2 - 8;
		ctx.fillText(fitText(ctx, node.label, maxWidth), node.x, node.y);
	});

	ctx.restore();

	// Full label tooltip for the hovered node, drawn in screen space (after restore)
	// so its text stays a fixed, readable size regardless of zoom level.
	if (hoveredNode) {
		const { x: sx, y: sy } = worldToScreen(hoveredNode.x, hoveredNode.y);
		const sr = hoveredNode.r * view.scale;

		ctx.font = "12px sans-serif";
		const paddingX = 6;
		const boxW = ctx.measureText(hoveredNode.label).width + paddingX * 2;
		const boxH = 20;
		const boxX = sx - boxW / 2;
		const boxY = sy - sr - boxH - 6;

		ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
		ctx.fillRect(boxX, boxY, boxW, boxH);

		ctx.fillStyle = "white";
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

	const clicked = nodes.find(node => Math.hypot(x - node.x, y - node.y) <= node.r);

	if (clicked) {
		console.log("Clicked:", clicked.id, clicked.label);
	}
})

canvas.addEventListener("dblclick", (e) => {
	const rect = canvas.getBoundingClientRect();
	const { x, y } = screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
	const clicked = nodes.find(node => Math.hypot(x - node.x, y - node.y) <= node.r);

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
	const found = nodes.find(n => Math.hypot(x - n.x, y - n.y) <= n.r);

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
	const zoomFactor = Math.exp(-e.deltaY * ZOOM_SPEED);
	view.scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, view.scale * zoomFactor));
	view.offsetX = sx - worldBefore.x * view.scale;
	view.offsetY = sy - worldBefore.y * view.scale;

	draw();
}, { passive: false })


loadTree();