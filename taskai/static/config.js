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
		chainColor: "#6366f1", // bold, distinct from both the plain tree edges and the dashed link edges
		chainWidth: 2.5,
		chainArrowSize: 10,
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
