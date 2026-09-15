// navigateGraph(direction, currentNode, graph) decides which node a
// direction key moves to. For a plain node, down/up walk the tree
// (children/parent) and left/right step across the whole depth level,
// wrapping at its ends. For a node that's part of a chain, down/up walk the
// chain itself (chainNext/chainPrev) instead — the relationship a chain node
// has to its own real children is `right`'s job, not `down`'s, since those
// children render as a row to the side, not below. Leaving that row happens
// two ways: `left` off its first entry steps back to the chain node itself,
// and `up` from anywhere in the row skips past the chain node straight to
// whatever came before it in the chain (or, at the chain's head, out to its
// ordinary tree parent).

// parentId -> childId memory of the last child navigated to under a given
// parent (ids, not node references, since nodes are rebuilt on every tree
// load). Lets `down` (a plain node's children) and `right` (a chain node's
// side row) return to where you last were; a stale id just misses and falls
// back to the first child.
const lastChildByParent = {};

function navigateGraph(direction, cur, graph) {
	let target = null;

	if (direction === "down") {
		if (isChainMember(cur)) {
			target = cur.chainNext || null;
		} else {
			if (!cur.children.length) return null;
			const remembered = lastChildByParent[cur.id];
			target = cur.children.find(c => c.id === remembered) || cur.children[0];
		}
	} else if (direction === "up") {
		if (isChainMember(cur)) {
			target = cur.chainPrev || cur.parent || null;
		} else if (cur.parent && isChainMember(cur.parent) && cur.parent.chainPrev) {
			target = cur.parent.chainPrev; // leaving a chain node's side row: skip the chain link, land on its predecessor
		} else {
			target = cur.parent || null;
		}
	} else if (direction === "right" && isChainMember(cur)) {
		if (!cur.children.length) return null;
		const remembered = lastChildByParent[cur.id];
		target = cur.children.find(c => c.id === remembered) || cur.children[0];
	} else if (direction === "left" && cur.parent && isChainMember(cur.parent) && cur.parent.children[0] === cur) {
		target = cur.parent; // first entry in a chain node's row: step back out to it
	} else if (direction === "left" || direction === "right") {
		// nodes sharing cur's y, sorted by x — the layout gives every node at a
		// given depth (or in the same chain row) the same y, so this doubles as
		// "the whole level" with no explicit depth bookkeeping. Wraps at the ends.
		const row = graph.nodes.filter(n => Math.abs(n.y - cur.y) < 1).sort((a, b) => a.x - b.x);
		const i = row.indexOf(cur);
		if (i === -1 || row.length < 2) return null;
		const step = direction === "right" ? 1 : -1;
		target = row[(i + step + row.length) % row.length];
	}

	if (!target || target === cur) return null;

	if (target.parent) lastChildByParent[target.parent.id] = target.id;

	return target;
}
