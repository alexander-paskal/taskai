// Drawing only: render(ctx, camera, graph, selectedNode, hoveredNode) draws
// one frame. Doesn't own any state, doesn't touch anything outside `ctx`.

function truncateWithEllipsis(ctx, text, maxWidth) {
	let truncated = text;
	while (truncated.length > 0 && ctx.measureText(truncated + "…").width > maxWidth) {
		truncated = truncated.slice(0, -1);
	}
	return truncated ? truncated + "…" : "…";
}

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
	if (!fullyFit) lines[lines.length - 1] = truncateWithEllipsis(ctx, lines[lines.length - 1], maxWidth);

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

// dashed edges from a node to each of its shadow (soft-link) children —
// uncoloured grey, the dash pattern alone distinguishes it from tree edges.
// Each edge fades out inside either node's square so it never crosses node
// content.
function drawLinkEdges(ctx, graph) {
	ctx.save();
	ctx.lineWidth = STYLE.edge.linkWidth;
	ctx.lineCap = "butt";
	ctx.setLineDash(STYLE.edge.linkDash);

	const rgb = STYLE.edge.linkColorRGB;
	const clear = `rgba(${rgb}, 0)`;
	const solid = `rgba(${rgb}, 0.9)`;

	function edge(from, to) {
		const dist = Math.hypot(to.x - from.x, to.y - from.y) || 1;
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
		if (node.chainNext) walk(node.chainNext);
	}
	graph.roots.forEach(walk);

	ctx.restore();
}

// bold, arrowed edges for chain successors — deliberately distinct from
// both the plain tree edges and the dashed shadow-link edges
function drawChainEdges(ctx, graph) {
	ctx.save();
	ctx.strokeStyle = STYLE.edge.chainColor;
	ctx.fillStyle = STYLE.edge.chainColor;
	ctx.lineWidth = STYLE.edge.chainWidth;
	ctx.lineCap = "round";

	function edge(from, to) {
		const dist = Math.hypot(to.x - from.x, to.y - from.y) || 1;
		const ux = (to.x - from.x) / dist;
		const uy = (to.y - from.y) / dist;
		const startX = from.x + ux * (from.size / 2);
		const startY = from.y + uy * (from.size / 2);
		const endX = to.x - ux * (to.size / 2);
		const endY = to.y - uy * (to.size / 2);

		ctx.beginPath();
		ctx.moveTo(startX, startY);
		ctx.lineTo(endX, endY);
		ctx.stroke();

		const arrow = STYLE.edge.chainArrowSize;
		const angle = Math.atan2(uy, ux);
		ctx.beginPath();
		ctx.moveTo(endX, endY);
		ctx.lineTo(endX - arrow * Math.cos(angle - Math.PI / 6), endY - arrow * Math.sin(angle - Math.PI / 6));
		ctx.lineTo(endX - arrow * Math.cos(angle + Math.PI / 6), endY - arrow * Math.sin(angle + Math.PI / 6));
		ctx.closePath();
		ctx.fill();
	}

	function walk(node) {
		if (node.chainNext) {
			edge(node, node.chainNext);
			walk(node.chainNext);
		}
		node.children.forEach(walk);
	}
	graph.roots.forEach(walk);

	ctx.restore();
}

function drawTreeEdges(ctx, graph) {
	ctx.strokeStyle = STYLE.colors.edge;
	ctx.lineWidth = STYLE.edge.width;
	ctx.lineCap = "round";

	function walk(node) {
		node.children.forEach(child => {
			if (child.isShadow) return; // shadow children get a dashed edge in drawLinkEdges instead
			ctx.beginPath();
			ctx.moveTo(node.x, node.y);
			ctx.lineTo(child.x, child.y);
			ctx.stroke();
			walk(child);
		});
		if (node.chainNext) walk(node.chainNext); // chain hop gets its own bold edge, drawn separately
	}
	graph.roots.forEach(walk);
}

function drawNode(ctx, node, isHovered, isSelected) {
	const half = node.size / 2;
	const isShadow = node.isShadow;
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

	if (!isShadow && node.due_by) {
		ctx.fillStyle = STYLE.colors.dueText;
		ctx.font = STYLE.node.idFont;
		ctx.textAlign = "right";
		ctx.textBaseline = "bottom";
		// "2026-12-31T00:00:00" -> "12/31" - compact, locale-agnostic
		const dueLabel = node.due_by.slice(5, 7) + "/" + node.due_by.slice(8, 10);
		ctx.fillText(dueLabel, nodeX + node.size - STYLE.node.idPadding, nodeY + node.size - STYLE.node.idPadding);
	}

	ctx.fillStyle = STYLE.colors.text;
	ctx.font = isShadow ? STYLE.node.ghostFont : STYLE.node.font;
	ctx.textAlign = "center";
	ctx.textBaseline = "middle";
	const maxWidth = node.size - STYLE.node.padding * 2;
	const lines = wrapText(ctx, node.label, maxWidth, STYLE.node.maxLines);
	const startY = node.y - ((lines.length - 1) * STYLE.node.lineHeight) / 2;
	lines.forEach((line, i) => ctx.fillText(line, node.x, startY + i * STYLE.node.lineHeight));

	ctx.restore();
}

// full-label tooltip for the hovered node, drawn in screen space so its text
// stays a fixed, readable size regardless of zoom level
function drawTooltip(ctx, camera, node) {
	const { x: sx, y: sy } = camera.worldToScreen(node.x, node.y);
	const halfScreen = (node.size / 2) * camera.scale;

	ctx.font = STYLE.tooltip.font;
	const boxW = ctx.measureText(node.label).width + STYLE.tooltip.paddingX * 2;
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
	ctx.fillText(node.label, sx, boxY + boxH / 2);
}

function drawEmptyState(ctx, canvas) {
	ctx.fillStyle = STYLE.colors.emptyStateText;
	ctx.font = STYLE.emptyState.font;
	ctx.textAlign = "center";
	ctx.textBaseline = "middle";
	ctx.fillText(STYLE.emptyState.message, canvas.width / 2, canvas.height / 2);
}

function render(ctx, camera, graph, selectedNode, hoveredNode) {
	const canvas = camera.canvas;

	ctx.fillStyle = STYLE.colors.background;
	ctx.fillRect(0, 0, canvas.width, canvas.height);

	if (!graph) return;

	if (!graph.nodes.length) {
		drawEmptyState(ctx, canvas);
		return;
	}

	ctx.save();
	ctx.translate(camera.offsetX, camera.offsetY);
	ctx.scale(camera.scale, camera.scale);

	drawTreeEdges(ctx, graph);
	drawLinkEdges(ctx, graph); // layered on top of tree edges, below chain edges and nodes
	drawChainEdges(ctx, graph);

	graph.nodes.forEach(node => drawNode(ctx, node, node === hoveredNode, node === selectedNode));

	ctx.restore();

	if (hoveredNode) drawTooltip(ctx, camera, hoveredNode);
}
