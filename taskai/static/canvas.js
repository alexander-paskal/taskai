// Visual configuration for the DAG canvas. Plain data on purpose — this will
// eventually be served by a backend endpoint (e.g. GET /api/style) so the
// look can be themed/configured server-side instead of hardcoded here.
const STYLE = {
	colors: {
		background: "#f5f6f8",
		nodeFill: "#ffffff",
		nodeFillHover: "#f3f6ff",
		nodeFillDone: "#e6f7ec",
		nodeFillDoneHover: "#d9f0e1",
		nodeBorder: "#e2e4ea",
		nodeBorderHover: "#4772fa",
		nodeBorderDone: "#a9dab9",
		text: "#23252b",
		idText: "#b4b9c4",
		statusText: "#e0924a",
		edge: "#dcdfe6",
		shadowNodeFill: "#ffffff", // same card fill as a real node — the dashed border + transparency set it apart, not a tint
		shadowNodeFillDone: "#eef7f0",
		shadowNodeBorder: "#c8ccd6", // same grey family as tree edges — the dash carries the meaning, not the colour
		shadowGlyph: "#a855f7", // the one colour accent kept on a shadow node
		tooltipBackground: "#ffffff",
		tooltipBorder: "#e2e4ea",
		tooltipText: "#23252b",
	},
	node: {
		size: 160, // full square side length, in world units
		cornerRadius: 14,
		font: "20px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
		lineHeight: 24,
		maxLines: 3,
		padding: 16,
		idFont: "11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
		idPadding: 12,
		borderWidth: 1.5,
		borderWidthHover: 2,
		shadowColor: "rgba(15, 23, 42, 0.10)",
		shadowBlur: 10,
		shadowOffsetY: 2,
		ghostOpacity: 0.92, // whole-node alpha for shadow (soft-link) nodes — only slightly transparent; the dashed border does most of the work
		ghostFont: "italic 20px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
		ghostDash: [5, 4], // dashed border for shadow nodes
		glyph: "↗", // ↗ drawn on a shadow node to mark it as a link
	},
	edge: {
		width: 1.25,
		linkWidth: 1.5,
		linkDash: [7, 6], // dash pattern (world units) for the parent -> shadow-node edge
		linkColorRGB: "150, 155, 168", // uncoloured grey; the dash is the cue, not a hue
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
		focusScale: 0.85,
		focusDurationMs: 250,
		// vertical screen position a focused node lands at, as a fraction of
		// canvas height from the top (0 = top, 1 = bottom); kept above center
		// so there's room below to see a focused node's children/grandchildren
		focusYRatio: 0.2,
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
let latestItemsById = {}; // full raw item data keyed by id, from the last /api/tree or /api/command response

// synthetic, never-drawn node sitting above the real root items. It's the
// nav anchor for top-level movement and the "selection" that means "the whole
// tree / nothing specific" — e.g. after `show all`, or clicking empty canvas.
// Never added to `nodes`, so it's never hit-tested, drawn, or bordered.
const ROOT_NODE_ID = "__root__";
const rootNode = { id: ROOT_NODE_ID, isRoot: true, label: "", size: 0, children: [], x: 0, y: 0 };

// the real item behind a node — for a shadow (soft-link) node that's the
// linked-to item (node.realId), not the synthetic shadow id
function itemForNode(node) {
	return node ? latestItemsById[node.realId || node.id] : null;
}

function flatten(node, list = []){
	list.push(node);
	node.children.forEach(child => flatten(child, list));
	return list;
}

// a "shadow" node: a lightweight, non-recursing stand-in for a soft-linked
// item (linked_ids), shown as a ghost child under the linking node instead
// of drawing an edge across the graph to the real one. `realId` points back
// at the actual item so selection/editing act on it, not the shadow.
function buildShadowNode(item, parentId) {
	return {
		id: `link:${parentId}:${item.id}`,
		realId: String(item.id),
		isShadow: true,
		label: item.name,
		size: STYLE.node.size,
		completed: item.completed,
		status: item.status,
		children: [],
	};
}

// builds a renderable node tree from the flat {id: item} map returned by /api/tree
function buildTree(itemsById, id) {
	const item = itemsById[id];
	const children = (item.child_ids || []).map(childId => buildTree(itemsById, childId));

	// soft links render as ghost children appended after the real ones
	(item.linked_ids || []).forEach(linkedId => {
		const linked = itemsById[linkedId];
		if (linked) children.push(buildShadowNode(linked, item.id));
	});

	const node = {
		id: String(item.id),
		label: item.name,
		size: STYLE.node.size,
		completed: item.completed,
		status: item.status,
		children,
	};

	// back-reference so navigation (navigate()) can walk up as well as down
	children.forEach(child => { child.parent = node; });

	return node;
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
	latestItemsById = itemsById;

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

	// keep the synthetic root pointing at the freshly-built real roots, and
	// park it just above them so it works as a nav origin
	rootNode.children = roots;
	roots.forEach(r => { r.parent = rootNode; });
	if (roots.length) {
		rootNode.x = roots.reduce((sum, r) => sum + r.x, 0) / roots.length;
		rootNode.y = Math.min(...roots.map(r => r.y)) - STYLE.layout.ySpacing;
	} else {
		rootNode.x = 0;
		rootNode.y = 0;
	}

	// the previously-selected node was rebuilt as a new object (or may no
	// longer exist) — re-resolve by id so selection survives a tree refresh
	if (selectedNode) {
		selectedNode = selectedNode.id === ROOT_NODE_ID
			? rootNode
			: nodes.find(n => n.id === selectedNode.id) || rootNode;
		if (typeof onNodeSelected === "function") {
			onNodeSelected(itemForNode(selectedNode));
		}
	}

	draw();
}

async function loadTree() {
	const res = await fetch("/api/tree");
	const itemsById = await res.json();
	applyTree(itemsById);
}

const canvas = document.getElementById("myCanvas");
const ctx = canvas.getContext("2d"); // get the canvas context I guess?

// pan/zoom view state: world coordinates map to screen as screen = world * scale + offset
const view = { offsetX: 0, offsetY: 0, scale: 1 };

function screenToWorld(sx, sy) {
	return { x: (sx - view.offsetX) / view.scale, y: (sy - view.offsetY) / view.scale };
}

function worldToScreen(wx, wy) {
	return { x: wx * view.scale + view.offsetX, y: wy * view.scale + view.offsetY };
}

// width (px) reserved on the right for the edit panel — the canvas fills the rest
let rightPanelWidth = 0;
let rightPanelWidthAnimId = null;

// keep in sync with the CSS width transition duration on .edit-panel in style.css
const PANEL_TRANSITION_MS = 200;

function applyCanvasSize() {
	canvas.width = window.innerWidth - rightPanelWidth;
	canvas.height = window.innerHeight;
}

function resizeCanvas() {
	applyCanvasSize();
	draw();
}
window.addEventListener("resize", resizeCanvas);

// rescales the zoom in proportion to how much the canvas width just changed
// (not just re-panning) so the same amount of world content stays in view
// instead of getting cropped by a narrower canvas, then re-anchors so
// `centerWorld` (whatever was visually centered before the change) stays
// centered after.
function _rescaleForWidthChange(oldWidth, startScale, centerWorld) {
	view.scale = oldWidth > 0
		? Math.min(STYLE.zoom.max, Math.max(STYLE.zoom.min, startScale * canvas.width / oldWidth))
		: startScale;

	view.offsetX = canvas.width / 2 - centerWorld.x * view.scale;
	view.offsetY = canvas.height / 2 - centerWorld.y * view.scale;
}

// jumps straight to `width` with no animation — for initial setup, where
// there's nothing on screen yet to transition from
function setRightPanelWidthInstant(width) {
	if (rightPanelWidthAnimId !== null) {
		cancelAnimationFrame(rightPanelWidthAnimId);
		rightPanelWidthAnimId = null;
	}

	const oldWidth = canvas.width;
	const startScale = view.scale;
	const centerWorld = screenToWorld(canvas.width / 2, canvas.height / 2);

	rightPanelWidth = width;
	applyCanvasSize();
	_rescaleForWidthChange(oldWidth, startScale, centerWorld);

	draw();
}

// eases the right-panel reservation (and the canvas size/zoom that follow
// it) to `targetWidth` over `duration`ms, matching the panel's own CSS
// transition so the graph resizes in step with it rather than snapping.
function setRightPanelWidth(targetWidth, duration = PANEL_TRANSITION_MS) {
	if (rightPanelWidthAnimId !== null) cancelAnimationFrame(rightPanelWidthAnimId);
	if (rightPanelWidth === targetWidth) return;

	const startWidth = rightPanelWidth;
	const startScale = view.scale;
	const oldWidth = canvas.width;
	const centerWorld = screenToWorld(canvas.width / 2, canvas.height / 2);
	const startTime = performance.now();

	function step(now) {
		const t = Math.min(1, (now - startTime) / duration);
		const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic

		rightPanelWidth = startWidth + (targetWidth - startWidth) * eased;
		applyCanvasSize();
		_rescaleForWidthChange(oldWidth, startScale, centerWorld);

		draw();

		rightPanelWidthAnimId = t < 1 ? requestAnimationFrame(step) : null;
	}

	rightPanelWidthAnimId = requestAnimationFrame(step);
}

// true if the world point (x, y) falls inside node's square
function hitTest(node, x, y) {
	const half = node.size / 2;
	return Math.abs(x - node.x) <= half && Math.abs(y - node.y) <= half;
}

// eases the view to `scale`, horizontally centering `node` and placing it
// at STYLE.zoom.focusYRatio down the screen (not vertically centered)
function focusOnNode(node, scale = STYLE.zoom.focusScale, duration = STYLE.zoom.focusDurationMs) {
	const startOffsetX = view.offsetX;
	const startOffsetY = view.offsetY;
	const startScale = view.scale;

	const targetOffsetX = canvas.width / 2 - node.x * scale;
	const targetOffsetY = canvas.height * STYLE.zoom.focusYRatio - node.y * scale;

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


// animates view to target offset/scale using the same ease-out cubic as focusOnNode
function easeView(targetOffsetX, targetOffsetY, targetScale, duration = STYLE.zoom.focusDurationMs) {
	const startOffsetX = view.offsetX;
	const startOffsetY = view.offsetY;
	const startScale = view.scale;
	const startTime = performance.now();

	function step(now) {
		const t = Math.min(1, (now - startTime) / duration);
		const eased = 1 - Math.pow(1 - t, 3);

		view.scale = startScale + (targetScale - startScale) * eased;
		view.offsetX = startOffsetX + (targetOffsetX - startOffsetX) * eased;
		view.offsetY = startOffsetY + (targetOffsetY - startOffsetY) * eased;

		draw();
		if (t < 1) requestAnimationFrame(step);
	}
	requestAnimationFrame(step);
}

// zoom around the canvas center by `factor` (e.g. 1.5 = in, 1/1.5 = out)
function canvasZoom(factor) {
	const cx = canvas.width / 2;
	const cy = canvas.height / 2;
	const worldCenter = screenToWorld(cx, cy);
	const newScale = Math.min(STYLE.zoom.max, Math.max(STYLE.zoom.min, view.scale * factor));
	easeView(cx - worldCenter.x * newScale, cy - worldCenter.y * newScale, newScale);
}

// pan by dx/dy screen pixels (positive dx = camera moves left, revealing content to the right)
function canvasPan(dx, dy) {
	easeView(view.offsetX + dx, view.offsetY + dy, view.scale);
}

// eases the view out until every real node fits on screen, with padding —
// used by `show all` / bare `show`
function fitAll(duration = STYLE.zoom.focusDurationMs) {
	if (!nodes.length) return;

	const half = STYLE.node.size / 2;
	const minX = Math.min(...nodes.map(n => n.x)) - half;
	const maxX = Math.max(...nodes.map(n => n.x)) + half;
	const minY = Math.min(...nodes.map(n => n.y)) - half;
	const maxY = Math.max(...nodes.map(n => n.y)) + half;

	const pad = 60; // screen px of breathing room around the content
	const scale = Math.min(
		STYLE.zoom.max,
		Math.max(
			STYLE.zoom.min,
			Math.min(
				(canvas.width - pad * 2) / (maxX - minX),
				(canvas.height - pad * 2) / (maxY - minY),
			),
		),
	);

	const cx = (minX + maxX) / 2;
	const cy = (minY + maxY) / 2;
	easeView(canvas.width / 2 - cx * scale, canvas.height / 2 - cy * scale, scale, duration);
}

// moves the selection relative to the current node along the node tree.
// The move is equivalent to a `show <target>`: the node becomes selected and
// the view eases + zooms to it (focusOnNode). Wraps around on both axes —
// past the last sibling loops to the first, past the bottom leaf loops back
// to rootNode (the top), and `up` from rootNode drops to the deepest node.
function navigate(direction) {
	const cur = selectedNode || rootNode;
	let target = null;

	if (direction === "down") {
		target = cur.children[0] || rootNode; // past the bottom -> wrap to the top
	} else if (direction === "up") {
		if (cur.parent) {
			target = cur.parent;
		} else {
			// at rootNode (the top) -> wrap to the bottom: follow the
			// first-child chain down to the deepest leaf
			target = cur;
			while (target.children[0]) target = target.children[0];
		}
	} else if (direction === "left" || direction === "right") {
		const sibs = cur.parent && cur.parent.children;
		if (!sibs || !sibs.length) return;
		const n = sibs.length;
		target = sibs[(sibs.indexOf(cur) + (direction === "right" ? 1 : -1) + n) % n];
	}

	if (!target || target === cur) return;

	selectedNode = target;
	if (typeof onNodeSelected === "function") onNodeSelected(itemForNode(target));
	if (target === rootNode) fitAll();
	else focusOnNode(target);
	draw();
}

// trims text, always appending an ellipsis, until "text…" fits maxWidth
function truncateWithEllipsis(ctx, text, maxWidth) {
	let truncated = text;
	while (truncated.length > 0 && ctx.measureText(truncated + "…").width > maxWidth) {
		truncated = truncated.slice(0, -1);
	}
	return truncated ? truncated + "…" : "…";
}

// returns text unchanged if it already fits maxWidth, else truncates with an ellipsis
function fitText(ctx, text, maxWidth) {
	if (ctx.measureText(text).width <= maxWidth) return text;
	return truncateWithEllipsis(ctx, text, maxWidth);
}

// wraps text into up to maxLines lines that each fit maxWidth, ellipsis-
// truncating the last line if there's still text left over after maxLines
function wrapText(ctx, text, maxWidth, maxLines) {
	const words = text.split(/\s+/).filter(Boolean);
	const lines = [];
	let currentLine = "";
	let nextWord = 0;

	while (nextWord < words.length && lines.length < maxLines) {
		const word = words[nextWord];
		const candidate = currentLine ? `${currentLine} ${word}` : word;

		if (!currentLine || ctx.measureText(candidate).width <= maxWidth) {
			currentLine = candidate;
			nextWord++;
		} else {
			lines.push(currentLine);
			currentLine = "";
		}
	}

	const fullyFit = nextWord >= words.length;
	if (currentLine) lines.push(currentLine);

	if (!fullyFit) {
		lines[lines.length - 1] = truncateWithEllipsis(ctx, lines[lines.length - 1], maxWidth);
	}

	return lines;
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

// dashed edges from a node to each of its shadow (soft-link) children. Uncoloured
// (grey) — the dash pattern alone distinguishes it from the solid tree edges.
// Each edge is drawn with a gradient stroke that's fully transparent inside
// either node's square and only opaque in the gap between them, so the line
// never crosses over node content.
function drawLinkEdges(ctx) {
	ctx.save();
	ctx.lineWidth = STYLE.edge.linkWidth;
	ctx.lineCap = "butt";
	ctx.setLineDash(STYLE.edge.linkDash);

	const rgb = STYLE.edge.linkColorRGB;
	const clear = `rgba(${rgb}, 0)`;
	const solid = `rgba(${rgb}, 0.9)`;

	function edge(from, to) {
		const dist = Math.hypot(to.x - from.x, to.y - from.y) || 1;
		// fraction of the line covered by each node's half-square
		const fromFrac = Math.min(0.49, (from.size / 2) / dist);
		const toFrac = Math.min(0.49, (to.size / 2) / dist);

		const grad = ctx.createLinearGradient(from.x, from.y, to.x, to.y);
		grad.addColorStop(0, clear);
		grad.addColorStop(Math.max(0, fromFrac - 0.001), clear);
		grad.addColorStop(fromFrac, solid);
		grad.addColorStop(1 - toFrac, solid);
		grad.addColorStop(Math.min(1, 1 - toFrac + 0.001), clear);
		grad.addColorStop(1, clear);

		ctx.strokeStyle = grad;
		ctx.beginPath();
		ctx.moveTo(from.x, from.y);
		ctx.lineTo(to.x, to.y);
		ctx.stroke();
	}

	function walk(node) {
		node.children.forEach(child => {
			if (child.isShadow) edge(node, child);
			else walk(child);
		});
	}
	roots.forEach(root => walk(root));

	ctx.restore();
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
			if (child.isShadow) return; // shadow children get a dashed edge in drawLinkEdges instead
			ctx.beginPath();
			ctx.moveTo(node.x, node.y);
			ctx.lineTo(child.x, child.y);
			ctx.stroke();
			drawLines(child);
		});
	}
	roots.forEach(root => drawLines(root));

	// Soft-link edges (linked_ids), layered on top of the tree edges but below the nodes
	drawLinkEdges(ctx);

	// Draw nodes
	nodes.forEach(node => {
		const half = node.size / 2;
		const isShadow = node.isShadow;
		const isHovered = node === hoveredNode;
		const isSelected = node === selectedNode;
		const nodeX = node.x - half;
		const nodeY = node.y - half;

		ctx.save();
		if (isShadow) ctx.globalAlpha = STYLE.node.ghostOpacity;

		ctx.save();
		if (!isShadow) {
			// shadow nodes stay flat — no drop shadow — so they read as secondary
			ctx.shadowColor = STYLE.node.shadowColor;
			ctx.shadowBlur = STYLE.node.shadowBlur;
			ctx.shadowOffsetY = STYLE.node.shadowOffsetY;
		}

		let fill;
		if (isShadow) fill = node.completed ? STYLE.colors.shadowNodeFillDone : STYLE.colors.shadowNodeFill;
		else if (node.completed) fill = isHovered ? STYLE.colors.nodeFillDoneHover : STYLE.colors.nodeFillDone;
		else fill = isHovered ? STYLE.colors.nodeFillHover : STYLE.colors.nodeFill;

		roundedRectPath(ctx, nodeX, nodeY, node.size, node.size, STYLE.node.cornerRadius);
		ctx.fillStyle = fill;
		ctx.fill();
		ctx.restore(); // drop the shadow before stroking the border

		let border = STYLE.colors.nodeBorder;
		if (isShadow) border = STYLE.colors.shadowNodeBorder;
		else if (node.completed) border = STYLE.colors.nodeBorderDone;
		if (isHovered || isSelected) border = STYLE.colors.nodeBorderHover;

		if (isShadow) ctx.setLineDash(STYLE.node.ghostDash);
		roundedRectPath(ctx, nodeX, nodeY, node.size, node.size, STYLE.node.cornerRadius);
		ctx.strokeStyle = border;
		ctx.lineWidth = (isHovered || isSelected) ? STYLE.node.borderWidthHover : STYLE.node.borderWidth;
		ctx.stroke();
		ctx.setLineDash([]);

		ctx.fillStyle = STYLE.colors.idText;
		ctx.font = STYLE.node.idFont;
		ctx.textAlign = "left";
		ctx.textBaseline = "top";
		ctx.fillText(isShadow ? node.realId : node.id, nodeX + STYLE.node.idPadding, nodeY + STYLE.node.idPadding);

		if (isShadow) {
			// a link glyph in the top-right marks this as a soft-link stand-in, not a real placement
			ctx.fillStyle = STYLE.colors.shadowGlyph;
			ctx.font = STYLE.node.idFont;
			ctx.textAlign = "right";
			ctx.textBaseline = "top";
			ctx.fillText(STYLE.node.glyph, nodeX + node.size - STYLE.node.idPadding, nodeY + STYLE.node.idPadding);
		} else if (node.status) {
			ctx.fillStyle = STYLE.colors.statusText;
			ctx.font = STYLE.node.idFont;
			ctx.textAlign = "right";
			ctx.textBaseline = "top";
			const maxStatusWidth = node.size / 2 - STYLE.node.idPadding;
			const statusLabel = fitText(ctx, node.status, maxStatusWidth);
			ctx.fillText(statusLabel, nodeX + node.size - STYLE.node.idPadding, nodeY + STYLE.node.idPadding);
		}

		ctx.fillStyle = STYLE.colors.text;
		ctx.font = isShadow ? STYLE.node.ghostFont : STYLE.node.font;
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		const maxWidth = node.size - STYLE.node.padding * 2;
		const lines = wrapText(ctx, node.label, maxWidth, STYLE.node.maxLines);
		const startY = node.y - ((lines.length - 1) * STYLE.node.lineHeight) / 2;
		lines.forEach((line, i) => {
			ctx.fillText(line, node.x, startY + i * STYLE.node.lineHeight);
		});

		ctx.restore();
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

// selection — persists across hover and drives the edit panel (see
// onNodeSelected, defined in editpanel.js). Never null: an empty/whole-tree
// selection is the synthetic rootNode.
let selectedNode = rootNode;

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

	selectedNode = clicked || rootNode; // empty canvas -> whole-tree selection
	if (typeof onNodeSelected === "function") {
		onNodeSelected(itemForNode(selectedNode));
	}
	draw();
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

// refetch on window focus so edits made elsewhere (e.g. the CLI) while this
// tab was in the background show up without needing a manual reload
window.addEventListener("focus", loadTree);
