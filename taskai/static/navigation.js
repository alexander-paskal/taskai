// navigateGraph(direction, currentNode, graph) decides which node a
// direction key moves to. Every direction has exactly one meaning, with no
// fallbacks:
//   - a plain (non-chain) node: down/up are children/parent, as ever
//   - a chain member: down/up are chainNext/chainPrev — the chain is the
//     spine you walk, and its side subtrees are never entered by accident.
//     The one exception is up from the head of a chain that sits at the top
//     level of the forest, which goes to the synthetic root (show all)
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
		// only a chain's head has a parent - a top-level one is the synthetic root
		target = inChain
			? cur.chainPrev || (cur.parent === graph.rootNode ? graph.rootNode : null)
			: cur.parent;
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
