// const canvas = document.getElementById('myCanvas');
// const ctx = canvas.getContext('2d');

// canvas.width = 400;
// canvas.height = 300;

// ctx.fillStyle = 'tomato';
// ctx.fillRect(20, 20, 100, 80);


const tree = {
  id: "root",
  label: "Root",
  x: 200, y: 50, r: 30,
  children: [
    {
      id: "child1",
      label: "Child 1",
      x: 100, y: 150, r: 25,
      children: [
        { id: "grandchild1", label: "GC 1", x: 60, y: 250, r: 20, children: [] }
      ]
    },
    {
      id: "child2",
      label: "Child 2",
      x: 300, y: 150, r: 25,
      children: []
    }
  ]
};



function flatten(node, list = []){
	list.push(node);
	node.children.forEach(child => flatten(child, list));
	return list;
}



const nodes = flatten(tree);
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
	drawLines(tree);
	
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


draw();