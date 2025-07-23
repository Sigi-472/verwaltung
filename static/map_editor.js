// State
let rooms = [];
let snapzones = [];
let currentMode = null; // 'draw-room', 'draw-snapzone', null
let drawingRoom = null;
let drawingSnapzone = null;
let selectedRoomId = null;
let dragData = null; // {type: 'room'|'snapzone', id, ...}
let resizeData = null;

let roomCounter = 1;
let snapzoneCounter = 1;

const container = document.getElementById('container');
const output = document.getElementById('output');
const drawRoomBtn = document.getElementById('draw-room-btn');
const drawSnapzoneBtn = document.getElementById('draw-snapzone-btn');
const snapzoneTypeSelect = document.getElementById('snapzone-type-select');
const cancelDrawBtn = document.getElementById('cancel-draw-btn');

const SNAPZONE_COLORS = {
	laptop: 'rgba(255,165,0,0.3)',
	stuhl: 'rgba(0,255,0,0.3)',
	tisch: 'rgba(255,0,255,0.3)',
};

const SNAPZONE_BORDER_COLORS = {
	laptop: 'orange',
	stuhl: 'limegreen',
	tisch: 'magenta',
};

function createElement(tag, cls, parent) {
	const el = document.createElement(tag);
	if(cls) el.className = cls;
	if(parent) parent.appendChild(el);
	return el;
}
function confirmDelete(msg) {
	return window.confirm(msg);
}
function updateOutput() {
	const exportData = {
		rooms: rooms.map(room => ({
			name: room.name,
			x: Math.round(room.x),
			y: Math.round(room.y),
			width: Math.round(room.width),
			height: Math.round(room.height)
		})),
		snapzones: snapzones.map(sz => ({
			type: sz.type,
			x: Math.round(sz.x),
			y: Math.round(sz.y),
			width: Math.round(sz.width),
			height: Math.round(sz.height)
		}))
	};
	output.textContent = JSON.stringify(exportData, null, 2);
}
function getMousePos(evt) {
	const rect = container.getBoundingClientRect();
	return {
		x: evt.clientX - rect.left,
		y: evt.clientY - rect.top
	};
}
function startDrawRoom() {
	currentMode = 'draw-room';
	drawRoomBtn.disabled = true;
	drawSnapzoneBtn.disabled = true;
	snapzoneTypeSelect.disabled = true;
	cancelDrawBtn.disabled = false;
	container.style.cursor = 'crosshair';
}
function startDrawSnapzone() {
	currentMode = 'draw-snapzone';
	drawRoomBtn.disabled = true;
	drawSnapzoneBtn.disabled = true;
	snapzoneTypeSelect.disabled = false;
	cancelDrawBtn.disabled = false;
	container.style.cursor = 'crosshair';
}
function cancelDraw() {
	currentMode = null;
	drawingRoom = null;
	drawingSnapzone = null;
	drawRoomBtn.disabled = false;
	drawSnapzoneBtn.disabled = false;
	snapzoneTypeSelect.disabled = false;
	cancelDrawBtn.disabled = true;
	container.style.cursor = 'default';
	renderAll();
}
function createRoomElement(room) {
	const el = createElement('div', 'room', container);
	el.style.left = room.x + 'px';
	el.style.top = room.y + 'px';
	el.style.width = room.width + 'px';
	el.style.height = room.height + 'px';
	el.dataset.id = room.id;

	const nameInput = createElement('input', 'name-input', el);
	nameInput.type = 'text';
	nameInput.value = room.name;
	nameInput.title = 'Raumname';
	nameInput.addEventListener('input', e => {
		room.name = e.target.value;
		updateOutput();
	});

	const delBtn = createElement('div', 'delete-btn', el);
	delBtn.textContent = '×';
	delBtn.title = 'Raum löschen';
	delBtn.addEventListener('click', e => {
		e.stopPropagation();
		if(confirmDelete(`Raum "${room.name || room.id}" löschen?`)) {
			rooms = rooms.filter(r => r.id !== room.id);
			updateOutput();
			renderAll();
		}
	});

	enableDragResize(el, 'room', room);

	return el;
}
function createSnapzoneElement(snapzone) {
	const el = createElement('div', 'snapzone', container);
	el.style.left = snapzone.x + 'px';
	el.style.top = snapzone.y + 'px';
	el.style.width = snapzone.width + 'px';
	el.style.height = snapzone.height + 'px';
	el.style.borderColor = SNAPZONE_BORDER_COLORS[snapzone.type] || 'gray';
	el.style.backgroundColor = SNAPZONE_COLORS[snapzone.type] || 'rgba(0,0,0,0.1)';
	el.dataset.id = snapzone.id;

	const typeSelect = createElement('select', 'type-select', el);
	['laptop','stuhl','tisch'].forEach(type => {
		const opt = document.createElement('option');
		opt.value = type;
		opt.textContent = type;
		if(type === snapzone.type) opt.selected = true;
		typeSelect.appendChild(opt);
	});
	typeSelect.addEventListener('change', e => {
		snapzone.type = e.target.value;
		el.style.borderColor = SNAPZONE_BORDER_COLORS[snapzone.type] || 'gray';
		el.style.backgroundColor = SNAPZONE_COLORS[snapzone.type] || 'rgba(0,0,0,0.1)';
		updateOutput();
	});

	const delBtn = createElement('div', 'delete-btn', el);
	delBtn.textContent = '×';
	delBtn.title = 'Snapzone löschen';
	delBtn.addEventListener('click', e => {
		e.stopPropagation();
		if(confirmDelete(`Snapzone "${snapzone.type}" löschen?`)) {
			snapzones = snapzones.filter(sz => sz.id !== snapzone.id);
			updateOutput();
			renderAll();
		}
	});

	enableDragResize(el, 'snapzone', snapzone);

	return el;
}
function enableDragResize(el, type, obj) {
	el.addEventListener('mousedown', e => {
		if(e.target.classList.contains('delete-btn') || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
		e.preventDefault();
		const rect = el.getBoundingClientRect();
		dragData = {
			type,
			id: obj.id,
			element: el,
			startX: e.clientX,
			startY: e.clientY,
			origX: obj.x,
			origY: obj.y,
			origWidth: obj.width,
			origHeight: obj.height,
			edge: getResizeEdge(e, rect),
		};
		if(dragData.edge) {
			resizeData = dragData;
			dragData = null;
		}
	});
}
function getResizeEdge(e, rect) {
	const margin = 8;
	const x = e.clientX - rect.left;
	const y = e.clientY - rect.top;
	const right = rect.width;
	const bottom = rect.height;
	let edge = '';
	if(x > right - margin) edge += 'r';
	else if(x < margin) edge += 'l';
	if(y > bottom - margin) edge += 'b';
	else if(y < margin) edge += 't';
	return edge || null;
}
window.addEventListener('mouseup', e => {
	if(dragData || resizeData) {
		dragData = null;
		resizeData = null;
		updateOutput();
	}
});

window.addEventListener('mousemove', e => {
	if(dragData) {
		e.preventDefault();
		const dx = e.clientX - dragData.startX;
		const dy = e.clientY - dragData.startY;
		const obj = (dragData.type === 'room' ? rooms : snapzones).find(o => o.id === dragData.id);
		if(!obj) return;
		obj.x = Math.max(0, dragData.origX + dx);
		obj.y = Math.max(0, dragData.origY + dy);
		renderAll();
		updateOutput();
	} else if(resizeData) {
		e.preventDefault();
		const dx = e.clientX - resizeData.startX;
		const dy = e.clientY - resizeData.startY;
		const obj = (resizeData.type === 'room' ? rooms : snapzones).find(o => o.id === resizeData.id);
		if(!obj) return;
		let x = obj.x, y = obj.y, w = resizeData.origWidth, h = resizeData.origHeight;
		if(resizeData.edge.includes('r')) w = Math.max(10, resizeData.origWidth + dx);
		if(resizeData.edge.includes('b')) h = Math.max(10, resizeData.origHeight + dy);
		if(resizeData.edge.includes('l')) { w = Math.max(10, resizeData.origWidth - dx); x = resizeData.origX + dx; }
		if(resizeData.edge.includes('t')) { h = Math.max(10, resizeData.origHeight - dy); y = resizeData.origY + dy; }
		obj.x = Math.max(0, x);
		obj.y = Math.max(0, y);
		obj.width = w;
		obj.height = h;
		renderAll();
		updateOutput();
	}
});

container.addEventListener('mousedown', e => {
	if(currentMode === 'draw-room') {
		const pos = getMousePos(e);
		drawingRoom = {x: pos.x, y: pos.y, width: 0, height: 0};
		drawTempRect('room', drawingRoom);
	} else if(currentMode === 'draw-snapzone') {
		const pos = getMousePos(e);
		drawingSnapzone = {x: pos.x, y: pos.y, width: 0, height: 0, type: snapzoneTypeSelect.value};
		drawTempRect('snapzone', drawingSnapzone);
	}
});
container.addEventListener('mousemove', e => {
	const pos = getMousePos(e);
	if(currentMode === 'draw-room' && drawingRoom) {
		drawingRoom.width = Math.max(1, pos.x - drawingRoom.x);
		drawingRoom.height = Math.max(1, pos.y - drawingRoom.y);
		drawTempRect('room', drawingRoom);
	} else if(currentMode === 'draw-snapzone' && drawingSnapzone) {
		drawingSnapzone.width = Math.max(1, pos.x - drawingSnapzone.x);
		drawingSnapzone.height = Math.max(1, pos.y - drawingSnapzone.y);
		drawTempRect('snapzone', drawingSnapzone);
	}
});
window.addEventListener('mouseup', e => {
	if(currentMode === 'draw-room' && drawingRoom) {
		if(drawingRoom.width > 5 && drawingRoom.height > 5) {
			rooms.push({
				id: 'r' + roomCounter++,
				name: '',
				x: drawingRoom.x,
				y: drawingRoom.y,
				width: drawingRoom.width,
				height: drawingRoom.height
			});
		}
		drawingRoom = null;
		cancelDraw();
	} else if(currentMode === 'draw-snapzone' && drawingSnapzone) {
		if(drawingSnapzone.width > 5 && drawingSnapzone.height > 5) {
			snapzones.push({
				id: 'sz' + snapzoneCounter++,
				type: drawingSnapzone.type,
				x: drawingSnapzone.x,
				y: drawingSnapzone.y,
				width: drawingSnapzone.width,
				height: drawingSnapzone.height
			});
		}
		drawingSnapzone = null;
		cancelDraw();
	}
});

function drawTempRect(type, rect) {
	removeTempRects();
	const temp = createElement('div', type === 'room' ? 'room' : 'snapzone', container);
	temp.style.left = rect.x + 'px';
	temp.style.top = rect.y + 'px';
	temp.style.width = rect.width + 'px';
	temp.style.height = rect.height + 'px';
	if(type === 'room') {
		temp.style.borderColor = 'rgba(0,0,255,0.8)';
		temp.style.backgroundColor = 'rgba(0,0,255,0.3)';
	} else {
		temp.style.borderColor = SNAPZONE_BORDER_COLORS[rect.type] || 'gray';
		temp.style.backgroundColor = SNAPZONE_COLORS[rect.type] || 'rgba(0,0,0,0.1)';
	}
	temp.id = 'temp-' + type;
}
function removeTempRects() {
	['temp-room','temp-snapzone'].forEach(id => {
		const el = document.getElementById(id);
		if(el) el.remove();
	});
}

function renderAll() {
	const overlay = document.getElementById('overlay');
	overlay.innerHTML = '';
	rooms.forEach(room => overlay.appendChild(createRoomElement(room)));
	snapzones.forEach(sz => overlay.appendChild(createSnapzoneElement(sz)));
	updateOutput();
}

drawRoomBtn.addEventListener('click', startDrawRoom);
drawSnapzoneBtn.addEventListener('click', startDrawSnapzone);
cancelDrawBtn.addEventListener('click', cancelDraw);
renderAll();
