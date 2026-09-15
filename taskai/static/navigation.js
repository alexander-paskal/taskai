// navigateGraph(direction, currentNode, graph) decides which node a
// direction key moves to. Arrow keys are primarily tree nav — down/up are
// children/parent, left/right step across the whole depth level (wrapping
// at its ends) — but fall back to the chain axis (chainNext/chainPrev) when
// the tree relationship in that direction is simply absent: a node with its
// own real children still descends into them (down never means "skip my
// children"), and a node with a tree parent still ascends to it, but a pure
// chain link (no children, or - always true for a non-head member - no tree
// parent) would otherwise be a dead end. "forward"/"back" remain the
// explicit, always-available chain axis regardless of tree relationships.

// parentId -> childId memory of the last child navigated to under a given
// parent (ids, not node references, since nodes are rebuilt on every tree
// load). Lets `down` return to where you last were; a stale id just misses
// and falls back to the first child.
const lastChildByParent = {};

function navigateGraph(direction, cur, graph) {
	let target = null;

	if (direction === "down") {
		if (cur.children.length) {
			const remembered = lastChildByParent[cur.id];
			target = cur.children.find(c => c.id === remembered) || cur.children[0];
		} else {
			target = cur.chainNext || null; // no real children - fall back to the chain
		}
	} else if (direction === "up") {
		target = cur.parent || cur.chainPrev || null; // no tree parent - fall back to the chain
	} else if (direction === "forward") {
		target = cur.chainNext || null;
	} else if (direction === "back") {
		target = cur.chainPrev || null;
	} else if (direction === "left" || direction === "right") {
		// nodes sharing cur's y, sorted by x — the layout gives every node at a
		// given depth the same y, so this doubles as "the whole level" with no
		// explicit depth bookkeeping. Wraps at the ends.
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
