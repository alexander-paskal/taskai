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


function draw() {
	ctx.clearRect(0, 0, canvas.width, canvas.height);
	
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
		ctx.fillStyle = "steelblue";
		ctx.fill();
		
		ctx.fillStyle = "white";
		ctx.font = "12px sans-serif";
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		ctx.fillText(node.label, node.x, node.y);
	});
}

canvas.addEventListener("click", (e) => {
	const rect = canvas.getBoundingClientRect();
	const mx = e.clientX - rect.left;
	const my = e.clientY - rect.top;
	
	const clicked = nodes.find(node => {
		const dx = mx - node.x;
		const dy = my - node.y;
		return Math.sqrt(dx*dx + dy*dy) <= node.r;
	});
	
	if (clicked) {
		console.log("Clicked:", clicked.id, clicked.label);
	}
})


// hovering color change
let hoveredNode = null;

function screenToWorld(sx, sy) {
	// return { x: (sx - view.offsetX) / view.scale, y: (sy - view.offsetY) / view.scale };
    return {x: sx, y: sy};
}

canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const {x, y } = screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
    const found = nodes.find(
        n => Math.hypot(
            x - n.x, 
            y-n.y
        ) <= n.r
    );

    if (found !== hoveredNode) {
        hoveredNode = found || null;
        canvas.style.cursor = found ? "pointer": "default";
        draw();
    }

})


loadTree();