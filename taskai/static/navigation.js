// navigateGraph(direction, currentNode, graph) decides which node a
// direction key moves to. Every direction has exactly one meaning, with no
// fallbacks:
//   - a plain (non-chain) node: down/up are children/parent, as ever
//   - a chain member: down is chainNext, up is chainPrev — the chain is the
//     spine you walk, and its side subtrees are never entered by accident.
//     A chain's head has no chainPrev, so up from it leaves the chain for the
//     head's tree parent (the synthetic root, i.e. show all, for a top-level
//     chain)
//   - into: chain member -> its subtree (remembered/first child), else nothing
//   - out: jump to the nearest chain member whose subtree contains the
//     current node (starting from the head of the node's own chain, if it's
//     in one). A top-level chain has no such owner, so its members go to the
//     synthetic root instead; anything else with no owner does nothing
//   - left/right step across the whole depth level (wrapping at its ends)
//   - forward/back: the explicit chain axis (console commands only)

// parentId -> childId memory of the last child navigated to under a given
// parent (ids, not node references, since nodes are rebuilt on every tree
// load). Lets `down`/`into` return to where you last were; a stale id just
// misses and falls back to the first child.
const lastChildByParent = {};

function rememberedChild(node) {
	if (!node.children.length) return null;
	const remembered = lastChildByParent[node.id];
	return node.children.find(c => c.id === remembered) || node.children[0];
}

function chainHead(node) {
	let n = node;
	while (n.chainPrev) n = n.chainPrev;
	return n;
}

// the nearest chain member whose subtree contains `node`. A chain's parent is
// its head's parent, so a chain member starts from its chain's head — never
// resolving to one of its own chain-mates.
function chainOwner(node) {
	for (let n = chainHead(node).parent; n; n = n.parent) {
		if (isChainMember(n)) return n;
	}
	return null;
}

function navigateGraph(direction, cur, graph) {
	let target = null;
	const inChain = isChainMember(cur);

	if (direction === "down") {
		target = inChain ? cur.chainNext : rememberedChild(cur);
	} else if (direction === "up") {
		// a node has either a chainPrev (a non-head chain member) or a tree
		// parent (a chain's head, or any plain node), never both, so this never
		// has to choose: walk back along the chain, and from its head leave it
		// for the tree parent (the synthetic root for a top-level chain)
		target = cur.chainPrev || cur.parent;
	} else if (direction === "into") {
		target = inChain ? rememberedChild(cur) : null;
	} else if (direction === "out") {
		target = chainOwner(cur)
			|| (inChain && chainHead(cur).parent === graph.rootNode ? graph.rootNode : null);
	} else if (direction === "forward") {
		target = cur.chainNext || null;
	} else if (direction === "back") {
		target = cur.chainPrev || null;
	} else if (direction === "left" || direction === "right") {
		// nodes sharing cur's growth coordinate, sorted along spread — the
		// layout gives every node at a given depth the same growth position
		// (see graph.js's place()), so this doubles as "the whole level" with
		// no explicit depth bookkeeping. Wraps at the ends.
		const [growth, spread] = STYLE.layout.growthDown ? ["y", "x"] : ["x", "y"];
		const row = graph.nodes.filter(n => Math.abs(n[growth] - cur[growth]) < 1).sort((a, b) => a[spread] - b[spread]);
		const i = row.indexOf(cur);
		if (i === -1 || row.length < 2) return null;
		const step = direction === "right" ? 1 : -1;
		target = row[(i + step + row.length) % row.length];
	}

	if (!target || target === cur) return null;

	if (target.parent) lastChildByParent[target.parent.id] = target.id;

	return target;
}
