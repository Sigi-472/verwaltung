from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Raum- und Snapzone Editor</title>
<style>
  body, html {
    margin: 0; padding: 0; height: 100%;
    font-family: Arial, sans-serif;
    background: #f0f0f0;
    user-select: none;
  }
  #container {
    position: relative;
    width: 1100px;
    height: 370px;
    margin: 20px auto;
    background: url('/static/sechste_etage.png') no-repeat top left;
    background-size: contain;
    border: 1px solid #ccc;
  }
  .room {
    position: absolute;
    border: 1px solid rgba(0,0,255,0.6);
    background-color: rgba(0, 0, 255, 0.2);
    box-sizing: border-box;
    overflow: visible;
  }
  .room .name-input {
    position: absolute;
    top: -25px;
    left: 0;
    width: 100px;
    font-size: 14px;
    padding: 2px 4px;
    border: 1px solid #666;
    border-radius: 3px;
    background: white;
  }
  .room .delete-btn {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 18px;
    height: 18px;
    background: red;
    color: white;
    font-weight: bold;
    text-align: center;
    line-height: 18px;
    cursor: pointer;
    border-radius: 50%;
    font-family: monospace;
    user-select: none;
  }

  .snapzone {
    position: absolute;
    border: 2px solid;
    box-sizing: border-box;
    cursor: move;
  }
  .snapzone .delete-btn {
    position: absolute;
    top: -10px;
    right: -10px;
    width: 18px;
    height: 18px;
    background: red;
    color: white;
    font-weight: bold;
    text-align: center;
    line-height: 18px;
    cursor: pointer;
    border-radius: 50%;
    font-family: monospace;
    user-select: none;
    z-index: 10;
  }
  .snapzone .type-select {
    position: absolute;
    top: -30px;
    left: 0;
    font-size: 12px;
  }

  #controls {
    width: 1100px;
    margin: 10px auto 0;
    display: flex;
    gap: 10px;
  }
  #controls button, #controls select {
    padding: 6px 10px;
    font-size: 14px;
    cursor: pointer;
  }

  #output {
    width: 1100px;
    margin: 20px auto;
    background: #222;
    color: #eee;
    padding: 10px;
    font-family: monospace;
    font-size: 14px;
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
    border-radius: 4px;
    user-select: all;
  }
</style>
</head>
<body>

<div id="controls">
  <button id="draw-room-btn">Raum zeichnen</button>
  <button id="draw-snapzone-btn" disabled>Snapzone zeichnen</button>
  <select id="snapzone-type-select" disabled>
    <option value="laptop">Laptop</option>
    <option value="stuhl">Stuhl</option>
    <option value="tisch">Tisch</option>
  </select>
  <button id="cancel-draw-btn" disabled>Abbrechen</button>
</div>

<div id="container"></div>

<pre id="output">// Räume und Snapzones werden hier angezeigt</pre>

<script>
// State
let rooms = [];
let currentMode = null; // 'draw-room', 'draw-snapzone', null
let drawingRoom = null;
let drawingSnapzone = null;
let selectedRoomId = null;
let dragData = null; // {type: 'room'|'snapzone', id, offsetX, offsetY, element}
let resizeData = null; // {type, id, edge, startX, startY, startWidth, startHeight}

// IDs
let roomCounter = 1;
let snapzoneCounter = 1;

const container = document.getElementById('container');
const output = document.getElementById('output');
const drawRoomBtn = document.getElementById('draw-room-btn');
const drawSnapzoneBtn = document.getElementById('draw-snapzone-btn');
const snapzoneTypeSelect = document.getElementById('snapzone-type-select');
const cancelDrawBtn = document.getElementById('cancel-draw-btn');

const SNAPZONE_COLORS = {
  laptop: 'rgba(255,165,0,0.3)', // orange
  stuhl: 'rgba(0,255,0,0.3)',   // green
  tisch: 'rgba(255,0,255,0.3)', // magenta
};

const SNAPZONE_BORDER_COLORS = {
  laptop: 'orange',
  stuhl: 'limegreen',
  tisch: 'magenta',
};

// Helpers
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
  const exportData = rooms.map(room => {
    return {
      name: room.name,
      x: Math.round(room.x),
      y: Math.round(room.y),
      width: Math.round(room.width),
      height: Math.round(room.height),
      snapzones: room.snapzones.map(sz => {
        return {
          type: sz.type,
          x: Math.round(sz.x),
          y: Math.round(sz.y),
          width: Math.round(sz.width),
          height: Math.round(sz.height)
        };
      })
    };
  });
  output.textContent = JSON.stringify(exportData, null, 2);
}
function getMousePos(evt) {
  const rect = container.getBoundingClientRect();
  return {
    x: evt.clientX - rect.left,
    y: evt.clientY - rect.top
  };
}
function isInside(a, b) {
  // a inside b? a,b = {x,y,width,height}
  return a.x >= b.x &&
         a.y >= b.y &&
         a.x + a.width <= b.x + b.width &&
         a.y + a.height <= b.y + b.height;
}

// Draw / Edit Logic
function startDrawRoom() {
  currentMode = 'draw-room';
  drawRoomBtn.disabled = true;
  drawSnapzoneBtn.disabled = true;
  snapzoneTypeSelect.disabled = true;
  cancelDrawBtn.disabled = false;
  container.style.cursor = 'crosshair';
}
function startDrawSnapzone() {
  if(selectedRoomId === null) {
    alert('Bitte zuerst einen Raum auswählen.');
    return;
  }
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
  drawSnapzoneBtn.disabled = selectedRoomId === null;
  snapzoneTypeSelect.disabled = selectedRoomId === null;
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

  // Name input
  const nameInput = createElement('input', 'name-input', el);
  nameInput.type = 'text';
  nameInput.value = room.name;
  nameInput.title = 'Raumname';
  nameInput.addEventListener('input', e => {
    room.name = e.target.value;
    updateOutput();
  });

  // Delete button
  const delBtn = createElement('div', 'delete-btn', el);
  delBtn.textContent = '×';
  delBtn.title = 'Raum löschen';
  delBtn.addEventListener('click', e => {
    e.stopPropagation();
    if(confirmDelete(`Raum "${room.name || room.id}" löschen?`)) {
      rooms = rooms.filter(r => r.id !== room.id);
      if(selectedRoomId === room.id) {
        selectedRoomId = null;
        drawSnapzoneBtn.disabled = true;
        snapzoneTypeSelect.disabled = true;
      }
      updateOutput();
      renderAll();
    }
  });

  // Drag & Resize for room
  enableDragResize(el, 'room', room);

  // highlight if selected
  if(selectedRoomId === room.id) el.style.borderColor = 'rgba(0,0,255,0.9)';
  else el.style.borderColor = 'rgba(0,0,255,0.6)';

  // Snapzones inside this room
  room.snapzones.forEach(snapzone => {
    const szEl = createSnapzoneElement(snapzone, room);
    el.appendChild(szEl);
  });

  el.addEventListener('click', e => {
    e.stopPropagation();
    if(selectedRoomId !== room.id) {
      selectedRoomId = room.id;
      drawSnapzoneBtn.disabled = false;
      snapzoneTypeSelect.disabled = false;
      renderAll();
    }
  });

  return el;
}
function createSnapzoneElement(snapzone, room) {
  const el = createElement('div', 'snapzone');
  el.style.left = snapzone.x + 'px';
  el.style.top = snapzone.y + 'px';
  el.style.width = snapzone.width + 'px';
  el.style.height = snapzone.height + 'px';
  el.style.borderColor = SNAPZONE_BORDER_COLORS[snapzone.type] || 'gray';
  el.style.backgroundColor = SNAPZONE_COLORS[snapzone.type] || 'rgba(0,0,0,0.1)';
  el.dataset.id = snapzone.id;

  // Type selector (editable)
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

  // Delete button
  const delBtn = createElement('div', 'delete-btn', el);
  delBtn.textContent = '×';
  delBtn.title = 'Snapzone löschen';
  delBtn.addEventListener('click', e => {
    e.stopPropagation();
    if(confirmDelete(`Snapzone "${snapzone.type}" löschen?`)) {
      const idx = room.snapzones.findIndex(sz => sz.id === snapzone.id);
      if(idx !== -1) {
        room.snapzones.splice(idx,1);
        updateOutput();
        renderAll();
      }
    }
  });

  // Drag & Resize for snapzone (relative to room container)
  enableDragResize(el, 'snapzone', snapzone, room);

  return el;
}

function enableDragResize(el, type, obj, parentRoom=null) {
  // Drag logic
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
      parentRoom,
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

    if(dragData.type === 'room') {
      // Move room
      dragData.element.style.left = dragData.origX + dx + 'px';
      dragData.element.style.top = dragData.origY + dy + 'px';
      dragData.element.style.width = dragData.origWidth + 'px';
      dragData.element.style.height = dragData.origHeight + 'px';

      // Update model
      const room = rooms.find(r => r.id === dragData.id);
      if(room) {
        room.x = dragData.origX + dx;
        room.y = dragData.origY + dy;
      }
    } else if(dragData.type === 'snapzone') {
      // Move snapzone relative to parent room
      const room = dragData.parentRoom;
      let newX = dragData.origX + dx;
      let newY = dragData.origY + dy;
      // Clamp inside room
      newX = Math.max(0, Math.min(newX, room.width - dragData.element.offsetWidth));
      newY = Math.max(0, Math.min(newY, room.height - dragData.element.offsetHeight));
      dragData.element.style.left = newX + 'px';
      dragData.element.style.top = newY + 'px';

      const snapzone = room.snapzones.find(sz => sz.id === dragData.id);
      if(snapzone) {
        snapzone.x = newX;
        snapzone.y = newY;
      }
    }
  } else if(resizeData) {
    e.preventDefault();
    const dx = e.clientX - resizeData.startX;
    const dy = e.clientY - resizeData.startY;

    if(resizeData.type === 'room') {
      const room = rooms.find(r => r.id === resizeData.id);
      if(!room) return;
      let x = room.x;
      let y = room.y;
      let w = resizeData.origWidth;
      let h = resizeData.origHeight;

      if(resizeData.edge.includes('r')) w = Math.max(20, resizeData.origWidth + dx);
      if(resizeData.edge.includes('b')) h = Math.max(20, resizeData.origHeight + dy);
      if(resizeData.edge.includes('l')) {
        w = Math.max(20, resizeData.origWidth - dx);
        x = resizeData.origX + dx;
      }
      if(resizeData.edge.includes('t')) {
        h = Math.max(20, resizeData.origHeight - dy);
        y = resizeData.origY + dy;
      }

      // Clamp to container boundaries
      x = Math.max(0, x);
      y = Math.max(0, y);
      if(x + w > container.clientWidth) w = container.clientWidth - x;
      if(y + h > container.clientHeight) h = container.clientHeight - y;

      room.x = x;
      room.y = y;
      room.width = w;
      room.height = h;
      renderAll();
      updateOutput();

    } else if(resizeData.type === 'snapzone') {
      const room = resizeData.parentRoom;
      const snapzone = room.snapzones.find(sz => sz.id === resizeData.id);
      if(!snapzone) return;
      let x = snapzone.x;
      let y = snapzone.y;
      let w = resizeData.origWidth;
      let h = resizeData.origHeight;

      if(resizeData.edge.includes('r')) w = Math.max(10, resizeData.origWidth + dx);
      if(resizeData.edge.includes('b')) h = Math.max(10, resizeData.origHeight + dy);
      if(resizeData.edge.includes('l')) {
        w = Math.max(10, resizeData.origWidth - dx);
        x = resizeData.origX + dx;
      }
      if(resizeData.edge.includes('t')) {
        h = Math.max(10, resizeData.origHeight - dy);
        y = resizeData.origY + dy;
      }

      // Clamp inside room
      x = Math.max(0, x);
      y = Math.max(0, y);
      if(x + w > room.width) w = room.width - x;
      if(y + h > room.height) h = room.height - y;

      snapzone.x = x;
      snapzone.y = y;
      snapzone.width = w;
      snapzone.height = h;
      renderAll();
      updateOutput();
    }
  }
});

// Drawing new rooms and snapzones
container.addEventListener('mousedown', e => {
  if(currentMode === 'draw-room') {
    const pos = getMousePos(e);
    drawingRoom = {x: pos.x, y: pos.y, width: 0, height: 0};
    // Temporarily create a visual rect
    drawTempRect('room', drawingRoom);
  } else if(currentMode === 'draw-snapzone') {
    if(selectedRoomId === null) return;
    const room = rooms.find(r => r.id === selectedRoomId);
    const pos = getMousePos(e);
    // snapzone coords relative to room:
    const relX = pos.x - room.x;
    const relY = pos.y - room.y;
    if(relX < 0 || relY < 0 || relX > room.width || relY > room.height) return; // outside room

    drawingSnapzone = {x: relX, y: relY, width: 0, height: 0, type: snapzoneTypeSelect.value};
    drawTempRect('snapzone', drawingSnapzone, room);
  }
});
container.addEventListener('mousemove', e => {
  if(currentMode === 'draw-room' && drawingRoom) {
    const pos = getMousePos(e);
    drawingRoom.width = Math.max(1, pos.x - drawingRoom.x);
    drawingRoom.height = Math.max(1, pos.y - drawingRoom.y);
    drawTempRect('room', drawingRoom);
  } else if(currentMode === 'draw-snapzone' && drawingSnapzone) {
    const room = rooms.find(r => r.id === selectedRoomId);
    const pos = getMousePos(e);
    let w = pos.x - room.x - drawingSnapzone.x;
    let h = pos.y - room.y - drawingSnapzone.y;
    w = Math.max(1, w);
    h = Math.max(1, h);

    // Clamp inside room
    if(drawingSnapzone.x + w > room.width) w = room.width - drawingSnapzone.x;
    if(drawingSnapzone.y + h > room.height) h = room.height - drawingSnapzone.y;

    drawingSnapzone.width = w;
    drawingSnapzone.height = h;
    drawTempRect('snapzone', drawingSnapzone, room);
  }
});
window.addEventListener('mouseup', e => {
  if(currentMode === 'draw-room' && drawingRoom) {
    // Finalize room
    if(drawingRoom.width > 5 && drawingRoom.height > 5) {
      const newRoom = {
        id: 'r' + roomCounter++,
        name: '',
        x: drawingRoom.x,
        y: drawingRoom.y,
        width: drawingRoom.width,
        height: drawingRoom.height,
        snapzones: []
      };
      rooms.push(newRoom);
      selectedRoomId = newRoom.id;
      drawSnapzoneBtn.disabled = false;
      snapzoneTypeSelect.disabled = false;
    }
    drawingRoom = null;
    currentMode = null;
    drawRoomBtn.disabled = false;
    drawSnapzoneBtn.disabled = selectedRoomId === null;
    snapzoneTypeSelect.disabled = selectedRoomId === null;
    cancelDrawBtn.disabled = true;
    removeTempRects();
    renderAll();
    updateOutput();
  } else if(currentMode === 'draw-snapzone' && drawingSnapzone) {
    // Finalize snapzone inside selected room
    if(drawingSnapzone.width > 5 && drawingSnapzone.height > 5) {
      const room = rooms.find(r => r.id === selectedRoomId);
      if(room) {
        room.snapzones.push({
          id: 'sz' + snapzoneCounter++,
          type: drawingSnapzone.type,
          x: drawingSnapzone.x,
          y: drawingSnapzone.y,
          width: drawingSnapzone.width,
          height: drawingSnapzone.height
        });
      }
    }
    drawingSnapzone = null;
    currentMode = null;
    drawRoomBtn.disabled = false;
    drawSnapzoneBtn.disabled = selectedRoomId === null;
    snapzoneTypeSelect.disabled = selectedRoomId === null;
    cancelDrawBtn.disabled = true;
    removeTempRects();
    renderAll();
    updateOutput();
  }
});

function drawTempRect(type, rect, parentRoom=null) {
  removeTempRects();
  const temp = createElement('div', type === 'room' ? 'room' : 'snapzone', parentRoom ? null : container);
  if(parentRoom) parentRoom.appendChild(temp);

  temp.style.left = rect.x + 'px';
  temp.style.top = rect.y + 'px';
  temp.style.width = rect.width + 'px';
  temp.style.height = rect.height + 'px';

  if(type === 'room') {
    temp.style.borderColor = 'rgba(0,0,255,0.8)';
    temp.style.backgroundColor = 'rgba(0,0,255,0.3)';
  } else if(type === 'snapzone') {
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
  container.innerHTML = '';
  rooms.forEach(room => {
    const el = createRoomElement(room);
    container.appendChild(el);
  });
  updateOutput();
}

// Initial
drawRoomBtn.addEventListener('click', startDrawRoom);
drawSnapzoneBtn.addEventListener('click', startDrawSnapzone);
cancelDrawBtn.addEventListener('click', cancelDraw);

// Deselect room on container click
container.addEventListener('click', e => {
  selectedRoomId = null;
  drawSnapzoneBtn.disabled = true;
  snapzoneTypeSelect.disabled = true;
  renderAll();
});

renderAll();
updateOutput();

</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(debug=True)
