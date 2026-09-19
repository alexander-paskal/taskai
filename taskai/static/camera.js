// Camera: the pan/zoom view transform for the canvas, plus the side-panel
// width reservations that shrink/grow it. Operates on graphs and nodes
// passed in by the caller — it never stores a Graph itself, so it stays
// usable on its own.

const PANEL_TRANSITION_MS = 200; // keep in sync with the CSS transition on .edit-panel / .shortcut-panel

class Camera {
	// `onChange` is called after every state-changing step (an animation
	// frame, a resize, a wheel event) so the caller can redraw.
	constructor(canvas, onChange) {
		this.canvas = canvas;
		this.onChange = onChange;

		this.offsetX = 0;
		this.offsetY = 0;
		this.scale = 1;

		this.leftPanelWidth = 0;
		this.rightPanelWidth = 0;
		this._panelAnim = { left: null, right: null };

		this._applySize();
	}

	screenToWorld(sx, sy) {
		return { x: (sx - this.offsetX) / this.scale, y: (sy - this.offsetY) / this.scale };
	}

	worldToScreen(wx, wy) {
		return { x: wx * this.scale + this.offsetX, y: wy * this.scale + this.offsetY };
	}

	_applySize() {
		this.canvas.width = window.innerWidth - this.rightPanelWidth - this.leftPanelWidth;
		this.canvas.height = window.innerHeight;
		this.canvas.style.marginLeft = this.leftPanelWidth + "px"; // shove the canvas past the left panel
	}

	resize() {
		this._applySize();
		this.onChange();
	}

	// rescales zoom in proportion to how much the canvas width just changed
	// (not just re-panning) so the same amount of world content stays in view,
	// then re-anchors so `centerWorld` stays visually centered
	_rescaleForWidthChange(oldWidth, startScale, centerWorld) {
		this.scale = oldWidth > 0
			? Math.min(STYLE.zoom.max, Math.max(STYLE.zoom.min, startScale * this.canvas.width / oldWidth))
			: startScale;

		this.offsetX = this.canvas.width / 2 - centerWorld.x * this.scale;
		this.offsetY = this.canvas.height / 2 - centerWorld.y * this.scale;
	}

	// jumps a side's reservation straight to `width` with no animation — for
	// initial setup, where there's nothing on screen yet to transition from
	setPanelWidthInstant(side, width) {
		if (this._panelAnim[side] !== null) {
			cancelAnimationFrame(this._panelAnim[side]);
			this._panelAnim[side] = null;
		}

		const oldWidth = this.canvas.width;
		const startScale = this.scale;
		const centerWorld = this.screenToWorld(this.canvas.width / 2, this.canvas.height / 2);

		this[`${side}PanelWidth`] = width;
		this._applySize();
		this._rescaleForWidthChange(oldWidth, startScale, centerWorld);

		this.onChange();
	}

	// eases a side's reservation (and the canvas size/zoom that follow it) to
	// `targetWidth` over `duration`ms, matching the panel's own CSS transition
	// so the graph resizes in step with it rather than snapping
	setPanelWidth(side, targetWidth, duration = PANEL_TRANSITION_MS) {
		if (this._panelAnim[side] !== null) cancelAnimationFrame(this._panelAnim[side]);
		const startWidth = this[`${side}PanelWidth`];
		if (startWidth === targetWidth) return;

		const startScale = this.scale;
		const oldWidth = this.canvas.width;
		const centerWorld = this.screenToWorld(this.canvas.width / 2, this.canvas.height / 2);
		const startTime = performance.now();

		const step = (now) => {
			const t = Math.min(1, (now - startTime) / duration);
			const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic

			this[`${side}PanelWidth`] = startWidth + (targetWidth - startWidth) * eased;
			this._applySize();
			this._rescaleForWidthChange(oldWidth, startScale, centerWorld);

			this.onChange();

			this._panelAnim[side] = t < 1 ? requestAnimationFrame(step) : null;
		};

		this._panelAnim[side] = requestAnimationFrame(step);
	}

	// eases to `scale`, centering `node` along the spread axis and placing it
	// at STYLE.zoom.focusGrowthRatio across the screen along the growth axis
	// - not centered, so there's room to see its descendants, which render
	// further along growth from it
	focusOnNode(node, scale = STYLE.zoom.focusScale, duration = STYLE.zoom.focusDurationMs) {
		const startOffsetX = this.offsetX;
		const startOffsetY = this.offsetY;
		const startScale = this.scale;
		const startTime = performance.now();

		const step = (now) => {
			const t = Math.min(1, (now - startTime) / duration);
			const eased = 1 - Math.pow(1 - t, 3);

			this.scale = startScale + (scale - startScale) * eased;

			// recompute the target every frame from the current canvas size: a
			// side panel opening in step with this animation resizes the canvas
			// mid-flight, and a target captured once up front would leave the
			// node off-centre by half the width change
			const growthDown = STYLE.layout.growthDown;
			const targetOffsetX = this.canvas.width * (growthDown ? 0.5 : STYLE.zoom.focusGrowthRatio) - node.x * scale;
			const targetOffsetY = this.canvas.height * (growthDown ? STYLE.zoom.focusGrowthRatio : 0.5) - node.y * scale;

			this.offsetX = startOffsetX + (targetOffsetX - startOffsetX) * eased;
			this.offsetY = startOffsetY + (targetOffsetY - startOffsetY) * eased;

			this.onChange();
			if (t < 1) requestAnimationFrame(step);
		};

		requestAnimationFrame(step);
	}

	// animates to a target offset/scale using the same ease-out cubic as focusOnNode
	easeTo(targetOffsetX, targetOffsetY, targetScale, duration = STYLE.zoom.focusDurationMs) {
		const startOffsetX = this.offsetX;
		const startOffsetY = this.offsetY;
		const startScale = this.scale;
		const startTime = performance.now();

		const step = (now) => {
			const t = Math.min(1, (now - startTime) / duration);
			const eased = 1 - Math.pow(1 - t, 3);

			this.scale = startScale + (targetScale - startScale) * eased;
			this.offsetX = startOffsetX + (targetOffsetX - startOffsetX) * eased;
			this.offsetY = startOffsetY + (targetOffsetY - startOffsetY) * eased;

			this.onChange();
			if (t < 1) requestAnimationFrame(step);
		};
		requestAnimationFrame(step);
	}

	// eased zoom around the canvas center by `factor` (e.g. 1.5 = in, 1/1.5 = out)
	zoom(factor) {
		const cx = this.canvas.width / 2;
		const cy = this.canvas.height / 2;
		const worldCenter = this.screenToWorld(cx, cy);
		const newScale = Math.min(STYLE.zoom.max, Math.max(STYLE.zoom.min, this.scale * factor));
		this.easeTo(cx - worldCenter.x * newScale, cy - worldCenter.y * newScale, newScale);
	}

	// eased pan by dx/dy screen pixels (positive dx = camera moves left, revealing content to the right)
	pan(dx, dy) {
		this.easeTo(this.offsetX + dx, this.offsetY + dy, this.scale);
	}

	// immediate (non-eased) zoom, keeping the point under the cursor fixed — for wheel input
	zoomAtPoint(sx, sy, factor) {
		const worldBefore = this.screenToWorld(sx, sy);
		this.scale = Math.min(STYLE.zoom.max, Math.max(STYLE.zoom.min, this.scale * factor));
		this.offsetX = sx - worldBefore.x * this.scale;
		this.offsetY = sy - worldBefore.y * this.scale;
		this.onChange();
	}

	// eases the view out until every node in `graph` fits on screen, with padding
	fitAll(graph, duration = STYLE.zoom.focusDurationMs) {
		if (!graph.nodes.length) return;

		const half = STYLE.node.size / 2;
		const minX = Math.min(...graph.nodes.map(n => n.x)) - half;
		const maxX = Math.max(...graph.nodes.map(n => n.x)) + half;
		const minY = Math.min(...graph.nodes.map(n => n.y)) - half;
		const maxY = Math.max(...graph.nodes.map(n => n.y)) + half;

		const pad = 60; // screen px of breathing room around the content
		const scale = Math.min(
			// don't auto-zoom in past the focus threshold — a small subset
			// shouldn't fill the screen; the user can still wheel in past this.
			// Capped below focusScale so show-all always visibly zooms out
			// from a selected node, even when the content would fit larger
			STYLE.zoom.fitMaxScale,
			Math.max(
				STYLE.zoom.min,
				Math.min(
					(this.canvas.width - pad * 2) / (maxX - minX),
					(this.canvas.height - pad * 2) / (maxY - minY),
				),
			),
		);

		const cx = (minX + maxX) / 2;
		const cy = (minY + maxY) / 2;
		this.easeTo(this.canvas.width / 2 - cx * scale, this.canvas.height / 2 - cy * scale, scale, duration);
	}
}
