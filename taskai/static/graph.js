// The node graph: builds the tree/chain structure and its layout positions
// from the flat {id: item} map /api/tree returns, and answers the queries
// the rest of the app needs (id lookup, item lookup, hit-testing). A new
// Graph is built from scratch on every /api/tree or /api/command response
// rather than mutating the old one in place.

const ROOT_NODE_ID = "__root__";

// true if `node` is a link in some chain (head, middle, or tail alike) — such
// a node's own real children grow to the right instead of centering below it
function isChainMember(node) {
	return !!(node.chainNext || node.chainPrev);
}

function flatten(node, list = []) {
	list.push(node);
	node.children.forEach(child => flatten(child, list));
	if (node.chainNext) flatten(node.chainNext, list);
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

function buildTree(itemsById, id, seen = new Set()) {
	const item = itemsById[id];
	seen.add(id);
	const children = (item.child_ids || []).map(childId => buildTree(itemsById, childId, seen));

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
		due: item.due,
		color: item.color,
		children,
	};
	children.forEach(child => { child.parent = node; });

	// a chain member never has its own parent_id (only a prev_chain_id) — it's
	// reached here by walking next_chain_id from its predecessor, not built as
	// a separate forest root. `seen` guards against a cycle in the chain data.
	if (item.next_chain_id != null && itemsById[item.next_chain_id] && !seen.has(item.next_chain_id)) {
		node.chainNext = buildTree(itemsById, item.next_chain_id, seen);
		node.chainNext.chainPrev = node;
	}

	return node;
}

// bottom-up: gives every node a {left, right, height} footprint in grid units
// (not pixels — place() turns these into positions via xSpacing/ySpacing).
// `left`/`right` are how far the node's content reaches left/right of its own
// x — not a single symmetric width, because a chain node's reach is
// lopsided: nothing it owns ever renders left of its own column, so `left`
// is always just the node's own square. A plain node still centers its
// children below it the old way (left == right == half the children's
// combined width). A chain node instead pushes its own real children into a
// row to its right (each additional child stacking further right than the
// last), and makes its chain successor wait — straight down, but only after
// however many rows that side-subtree needs, so nothing overlaps it.
function measure(node) {
	const childBoxes = node.children.map(measure);

	if (isChainMember(node)) {
		const sideRight = childBoxes.length
			? 1 + childBoxes.reduce((sum, b) => sum + b.left + b.right, 0)
			: 0;
		const sideHeight = childBoxes.length ? Math.max(...childBoxes.map(b => b.height)) : 0;
		const chainBox = node.chainNext ? measure(node.chainNext) : { right: 0, height: 0 };

		node._childBoxes = childBoxes;
		node._sideHeight = sideHeight;
		node._left = 0.5; // only this node's own square ever reaches left of its x
		node._right = Math.max(0.5, sideRight, chainBox.right);
		node._height = 1 + sideHeight + chainBox.height;
	} else {
		const total = childBoxes.reduce((sum, b) => sum + b.left + b.right, 0);

		node._childBoxes = childBoxes;
		node._left = childBoxes.length ? total / 2 : 0.5;
		node._right = childBoxes.length ? total / 2 : 0.5;
		node._height = childBoxes.length ? 1 + Math.max(...childBoxes.map(b => b.height)) : 1;
	}

	return { left: node._left, right: node._right, height: node._height };
}

// top-down: places `node` at grid position (spread, growth) along the two
// abstract layout axes — resolved to world coordinates here. By default growth
// maps to screen Y and spread to screen X (a tree grows downward,
// siblings/chain side-rows fan out sideways); STYLE.layout.growthDown = false
// swaps them. That mapping lives entirely in the lines below; every recursive call
// below them just passes spread/growth values through unchanged, so it's the
// only place the DAG's orientation is decided. Then places descendants per
// the rule measure() used. A child is anchored at `spread + cursor +
// child.left` (not `cursor + width/2`) so its bounding box's leading edge
// lands exactly at `cursor` regardless of whether that child's own footprint
// is symmetric or lopsided.
function place(node, spread, growth) {
	if (STYLE.layout.growthDown) {
		node.x = STYLE.layout.marginX + spread * STYLE.layout.xSpacing;
		node.y = STYLE.layout.marginY + growth * STYLE.layout.ySpacing;
	} else {
		node.x = STYLE.layout.marginX + growth * STYLE.layout.xSpacing;
		node.y = STYLE.layout.marginY + spread * STYLE.layout.ySpacing;
	}

	if (isChainMember(node)) {
		let cursor = 1; // side row starts one column past the spine
		node.children.forEach((child, i) => {
			const box = node._childBoxes[i];
			place(child, spread + cursor + box.left, growth + 1);
			cursor += box.left + box.right;
		});
		if (node.chainNext) place(node.chainNext, spread, growth + 1 + node._sideHeight);
	} else {
		let cursor = -node._left;
		node.children.forEach((child, i) => {
			const box = node._childBoxes[i];
			place(child, spread + cursor + box.left, growth + 1);
			cursor += box.left + box.right;
		});
	}
}

function nodeContains(node, x, y) {
	const half = node.size / 2;
	return Math.abs(x - node.x) <= half && Math.abs(y - node.y) <= half;
}

class Graph {
	constructor(itemsById) {
		this.itemsById = itemsById;

		const rootIds = Object.values(itemsById)
			.filter(item => item.parent_id === null && item.prev_chain_id == null)
			.map(item => item.id);

		this.roots = rootIds.map(id => buildTree(itemsById, id));

		// lay the forest out as one more row of slots (never a chain itself), same
		// as any node's children, then add a bit of extra breathing room between
		// separate root trees on top of ordinary sibling spacing
		const superRoot = { children: this.roots };
		measure(superRoot);

		// treeGap is a spread-axis gap (roots spread out like any other
		// sibling row), so convert it with the spread axis's spacing - see place()
		const spreadSpacing = STYLE.layout.growthDown ? STYLE.layout.xSpacing : STYLE.layout.ySpacing;
		const extraGapUnits = STYLE.layout.treeGap / spreadSpacing;
		const totalWidth = superRoot._left + superRoot._right + Math.max(0, this.roots.length - 1) * extraGapUnits;
		let cursor = -totalWidth / 2;
		this.roots.forEach((root, i) => {
			if (i > 0) cursor += extraGapUnits;
			const box = superRoot._childBoxes[i];
			place(root, cursor + box.left, 0);
			cursor += box.left + box.right;
		});

		this.nodes = this.roots.flatMap(root => flatten(root));

		this.byId = {};
		this.nodes.forEach(node => { this.byId[node.id] = node; });

		// synthetic, never-drawn node sitting above the real roots — the nav
		// anchor for top-level movement and the "whole tree / nothing specific"
		// selection. Never added to `nodes`, so never hit-tested or drawn.
		this.rootNode = { id: ROOT_NODE_ID, isRoot: true, label: "", size: 0, children: this.roots, x: 0, y: 0 };
		this.roots.forEach(r => { r.parent = this.rootNode; });
		if (this.roots.length) {
			// one step back along growth from the first root, centered on
			// spread across all of them
			const meanX = this.roots.reduce((sum, r) => sum + r.x, 0) / this.roots.length;
			const meanY = this.roots.reduce((sum, r) => sum + r.y, 0) / this.roots.length;
			if (STYLE.layout.growthDown) {
				this.rootNode.x = meanX;
				this.rootNode.y = Math.min(...this.roots.map(r => r.y)) - STYLE.layout.ySpacing;
			} else {
				this.rootNode.x = Math.min(...this.roots.map(r => r.x)) - STYLE.layout.xSpacing;
				this.rootNode.y = meanY;
			}
		}
	}

	getNode(id) {
		if (id === ROOT_NODE_ID) return this.rootNode;
		return this.byId[id] || null;
	}

	// the real item behind a node — for a shadow (soft-link) node that's the
	// linked-to item (node.realId), not the synthetic shadow id
	itemFor(node) {
		return node ? this.itemsById[node.realId || node.id] : null;
	}

	hitTest(x, y) {
		return this.nodes.find(node => nodeContains(node, x, y)) || null;
	}
}
