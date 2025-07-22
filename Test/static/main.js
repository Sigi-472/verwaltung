const floorplan = document.getElementById("floorplan");
let scale = 1;
let offsetX = 0;
let offsetY = 0;
let objId = 0;
let selectedShape = null;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;
let startOffsetX = 0;
let startOffsetY = 0;

const SNAPZONE_COLORS = {
  laptop: "rgba(100, 149, 237, 0.5)", // cornflowerblue, halbtransparent
  stuhl: "rgba(144, 238, 144, 0.5)",  // lightgreen
  // weitere Typen hier, z.B.:
  // tisch: "rgba(255, 165, 0, 0.5)",  // orange
};

// Bildquellen
const shapeImages = {
  laptop: "/static/Laptop_Bild.png",
  stuhl: "/static/Stuhl_Bild.png"
};

const DEFAULT_SNAPZONE_WIDTH = 40;
const DEFAULT_SNAPZONE_HEIGHT = 40;

// Räume
const roomsData = [
  {
    name: "701",
    x: 0,
    y: 0,
    width: 200,
    height: 150,
    snapzones: [
      { type: "laptop", x: 10, y: 10, width: 60, height: 40 },
      { type: "stuhl", x: 80, y: 100, width: 40, height: 40 }
    ],
  },
  {
    name: "703",
    x: 220,
    y: 0,
    width: 180,
    height: 160,
    snapzones: [
      { type: "stuhl", x: 20, y: 20, width: 40, height: 40 },
      { type: "laptop", x: 100, y: 50, width: 55, height: 35 }
    ],
  },
  {
    name: "705",
    x: 440,
    y: 0,
    width: 210,
    height: 140,
    snapzones: [
      { type: "laptop", x: 15, y: 15, width: 50, height: 30 },
      { type: "stuhl", x: 130, y: 80 }
    ],
  },
  {
    name: "707",
    x: 660,
    y: 0,
    width: 190,
    height: 155,
    snapzones: [
      { type: "stuhl", x: 20, y: 30, width: 45, height: 45 },
      { type: "laptop", x: 100, y: 20, width: 60, height: 40 },
      { type: "laptop", x: 140, y: 110, width: 40, height: 35 }
    ],
  },
  {
    name: "709",
    x: 880,
    y: 0,
    width: 200,
    height: 150,
    snapzones: [
      { type: "stuhl", x: 40, y: 30, width: 40, height: 40 }
    ],
  },
  {
    name: "711",
    x: 0,
    y: 180,
    width: 220,
    height: 170,
    snapzones: [
      { type: "laptop", x: 15, y: 25, width: 55, height: 35 },
      { type: "stuhl", x: 70, y: 90, width: 40, height: 40 }
    ],
  },
  {
    name: "713",
    x: 220,
    y: 180,
    width: 200,
    height: 160,
    snapzones: [
      { type: "stuhl", x: 10, y: 20, width: 40, height: 40 }
    ],
  },
  {
    name: "715",
    x: 440,
    y: 180,
    width: 210,
    height: 150,
    snapzones: [
      { type: "laptop", x: 40, y: 40, width: 60, height: 40 },
      { type: "stuhl", x: 110, y: 100, width: 40, height: 40 }
    ],
  },
  {
    name: "717",
    x: 660,
    y: 180,
    width: 195,
    height: 155,
    snapzones: [
      { type: "stuhl", x: 15, y: 50, width: 40, height: 40 },
      { type: "laptop", x: 90, y: 80, width: 55, height: 35 }
    ],
  },
  {
    name: "719",
    x: 880,
    y: 180,
    width: 205,
    height: 165,
    snapzones: [
      { type: "stuhl", x: 30, y: 30, width: 40, height: 40 },
      { type: "laptop", x: 110, y: 110, width: 60, height: 40 },
      { type: "stuhl", x: 160, y: 50, width: 40, height: 40 }
    ],
  },
];

const rooms = {};

// Räume + Snapzones erzeugen
function createRoomElement(data) {
  const room = document.createElement("div");
  room.className = "room";
  room.style.left = data.x + "px";
  room.style.top = data.y + "px";

  if (data.width) {
    room.style.width = data.width + "px";
  }
  if (data.height) {
    room.style.height = data.height + "px";
  }

  room.dataset.name = data.name;
  return room;
}

function createLabel(name) {
  const label = document.createElement("div");
  label.className = "room-label";
  label.textContent = "Raum " + name;
  return label;
}

function createCounter() {
  const counter = document.createElement("div");
  counter.className = "room-counter";
  counter.textContent = "0 Objekt(e)";
  counter.dataset.count = "0";
  return counter;
}
// Globaler Zähler für Snapzone-IDs pro Typ
let snapzoneCounter = 0; // Am Anfang deines Skripts

function createSnapzone({ type, x, y, width, height }) {
  const snapzone = document.createElement("div");
  snapzone.className = "snapzone " + type;
  snapzone.dataset.shape = type;

  snapzone.style.left = x + "px";
  snapzone.style.top = y + "px";
  snapzone.style.width = (width || DEFAULT_SNAPZONE_WIDTH) + "px";
  snapzone.style.height = (height || DEFAULT_SNAPZONE_HEIGHT) + "px";

  snapzone.style.backgroundColor = {
    laptop: "rgba(100, 149, 237, 0.3)",
    stuhl: "rgba(144, 238, 144, 0.3)"
  }[type] || "rgba(200,200,200,0.2)";

  snapzone.style.pointerEvents = "none";
  snapzone.title = "Snapzone: " + type;

  // 🔧 WICHTIG: Snapzone-ID zuweisen
  snapzone.dataset.snapzoneId = `${type}-${++snapzoneCounter}`;

  return snapzone;
}


function createRoom(data) {
  const room = createRoomElement(data);
  const label = createLabel(data.name);
  const counter = createCounter();

  room.appendChild(label);
  room.appendChild(counter);

  const snapzones = {};
  if (Array.isArray(data.snapzones)) {
    data.snapzones.forEach(snapData => {
      const snapzone = createSnapzone(snapData);
      room.appendChild(snapzone);

      // snapzones-Objekt nach Typ gruppieren (falls mehrere Snapzones vom gleichen Typ)
      if (!snapzones[snapData.type]) snapzones[snapData.type] = [];
      snapzones[snapData.type].push(snapzone);
    });
  }

  return { room, counter, snapzones };
}

function createRooms() {
  roomsData.forEach(data => {
    const { room, counter, snapzones } = createRoom(data);
    floorplan.appendChild(room);

    rooms[data.name] = {
      el: room,
      counterEl: counter,
      snapzones,
      objects: []
    };
  });
}

// Objekt erzeugen
function createObject(shape) {
  objId++;
  const obj = document.createElement("img");
  obj.className = "object";
  obj.dataset.id = objId;
  obj.dataset.room = "";
  obj.dataset.shape = shape;
  obj.src = shapeImages[shape];
  obj.style.left = "10px";
  obj.style.top = "10px";
  obj.draggable = false;

  floorplan.appendChild(obj);

  // Erstes Zimmer zuweisen + Counter aktualisieren
  const firstRoom = Object.values(rooms)[0];
  rooms[firstRoom.el.dataset.name].objects.push(obj);
  obj.dataset.room = firstRoom.el.dataset.name;
  updateCounter(firstRoom);

  makeDraggable(obj);
}

function updateCounter(room) {
  const count = room.objects.length;
  room.counterEl.textContent = `${count} Objekt(e)`;
  room.counterEl.dataset.count = count;
}

function isSnapzoneOccupied(room, shape, snapzone, draggedEl = null) {
  const snapzoneId = snapzone.dataset.snapzoneId;
  console.log(`[isSnapzoneOccupied] Prüfe Belegung für Shape "${shape}" und Snapzone-ID: ${snapzoneId}`);

  const objects = room.objects || [];

  for (const obj of objects) {
    if (
      obj.dataset.shape === shape &&
      obj.dataset.snapped === "true" &&
      obj.dataset.snapzoneId === snapzoneId
    ) {
      // Falls das Objekt das aktuell gezogene ist → ignorieren!
      if (draggedEl && obj === draggedEl) {
        console.log(`[isSnapzoneOccupied] Aktuelles Objekt selbst erkannt – ignoriere.`);  
        continue;
      }

      console.log(`[isSnapzoneOccupied] Snapzone belegt durch Objekt ${obj.dataset.id}`);
      return true;
    }
  }

  console.log(`[isSnapzoneOccupied] Snapzone ist frei.`);
  return false;
}




function snapObjectToZone(el, room) {
  const shape = el.dataset.shape;
  console.log(`[snapObjectToZone] Starte Snapping für Shape: "${shape}"`);

  let snapzones = room.snapzones[shape];
  if (!snapzones) {
    console.error(`[snapObjectToZone] Keine Snapzones für Shape "${shape}" gefunden!`);
    el.dataset.snapped = "false";
    return;
  }

  if (!Array.isArray(snapzones)) {
    snapzones = [snapzones];
    console.log(`[snapObjectToZone] Snapzones für "${shape}" in Array umgewandelt`);
  }

  console.log(`[snapObjectToZone] Anzahl Snapzones für "${shape}": ${snapzones.length}`);

  let snapzone = null;
  for (const [index, zone] of snapzones.entries()) {
    const zoneElement = Array.isArray(zone) ? zone[0] : zone;

    if (!(zoneElement instanceof HTMLElement)) {
      console.warn(`[snapObjectToZone] Snapzone #${index} ist kein HTMLElement:`, zoneElement);
      continue;
    }

    console.log(`[snapObjectToZone] Prüfe Snapzone #${index} (Shape: ${shape})`);

    if (!isSnapzoneOccupied(room, shape, zoneElement)) {
      console.log(`[snapObjectToZone] Snapzone #${index} ist frei. Wähle diese zum Snappen.`);
      snapzone = zoneElement;
      break;
    } else {
      console.log(`[snapObjectToZone] Snapzone #${index} ist bereits belegt.`);
    }
  }

  if (!snapzone) {
    console.warn(`[snapObjectToZone] Keine freie Snapzone für Shape "${shape}" gefunden.`);
    el.dataset.snapped = "false";
    return;
  }

  const floorplanRect = floorplan.getBoundingClientRect();
  const snapRect = snapzone.getBoundingClientRect();

  let left = (snapRect.left - floorplanRect.left) / scale + (snapzone.offsetWidth - el.offsetWidth) / 2;
  let top = (snapRect.top - floorplanRect.top) / scale + (snapzone.offsetHeight - el.offsetHeight) / 2;

  console.log(`[snapObjectToZone] Snapzone Position (px relativ Floorplan): left=${left}, top=${top}`);

  el.style.left = left + "px";
  el.style.top = top + "px";

  el.dataset.snapped = "true";

  console.log(`[snapObjectToZone] Objekt gesnappt an Snapzone #${snapzones.indexOf(snapzone)} mit Shape "${shape}"`);
}




function updateZIndex(obj, room) {
  obj.style.zIndex = 300;
}

function makeDraggable(el) {
  let dragging = false;
  let dragOffsetX = 0;
  let dragOffsetY = 0;

  function getElementCenterOffset(e, el) {
    const elRect = el.getBoundingClientRect();
    const offsetX = e.clientX - (elRect.left + elRect.width / 2);
    const offsetY = e.clientY - (elRect.top + elRect.height / 2);
    //console.log("Center offset:", { offsetX, offsetY });
    return { offsetX, offsetY };
  }

  function startDragging(e) {
    e.preventDefault();
    dragging = true;
    el.style.cursor = "grabbing";
    console.log("Dragging started");

    const offsets = getElementCenterOffset(e, el);
    dragOffsetX = offsets.offsetX;
    dragOffsetY = offsets.offsetY;

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  function getMousePosRelativeToFloorplan(ev) {
    const floorplanRect = floorplan.getBoundingClientRect();
    let mouseX = ev.clientX - floorplanRect.left - el.offsetWidth / 2 - dragOffsetX;
    let mouseY = ev.clientY - floorplanRect.top - el.offsetHeight / 2 - dragOffsetY;
    //console.log("Raw mouse position relative to floorplan:", { mouseX, mouseY });
    return { mouseX, mouseY };
  }

  function scaleAndClampPosition(mouseX, mouseY) {
    let x = mouseX / scale;
    let y = mouseY / scale;

    x = Math.min(Math.max(0, x), floorplan.offsetWidth - el.offsetWidth);
    y = Math.min(Math.max(0, y), floorplan.offsetHeight - el.offsetHeight);

    //console.log("Scaled and clamped position:", { x, y });
    return { x, y };
  }

  function moveElement(x, y) {
    el.style.left = x + "px";
    el.style.top = y + "px";
    el.dataset.snapped = "false";
    //console.log(`Element moved to (${x}, ${y})`);
  }

  function onMouseMove(ev) {
    if (!dragging) return;

    const { mouseX, mouseY } = getMousePosRelativeToFloorplan(ev);
    const { x, y } = scaleAndClampPosition(mouseX, mouseY);
    moveElement(x, y);
  }

  function findRoomContainingElementCenter(el) {
    const objRect = el.getBoundingClientRect();
    const cx = objRect.left + objRect.width / 2;
    const cy = objRect.top + objRect.height / 2;
    //console.log("Element center coordinates:", { cx, cy });

    let foundRoom = null;
    Object.values(rooms).forEach(room => {
      const rRect = room.el.getBoundingClientRect();
      if (cx > rRect.left && cx < rRect.right && cy > rRect.top && cy < rRect.bottom) {
        foundRoom = room;
        console.log("Found room containing element:", room.el.dataset.name);
      }
    });
    if (!foundRoom) console.log("No room found containing element");
    return foundRoom;
  }

  function removeFromOldRoom(el) {
    const oldRoomName = el.dataset.room;
    if (rooms[oldRoomName]) {
      const oldRoom = rooms[oldRoomName];
      oldRoom.objects = oldRoom.objects.filter(o => o !== el);
      updateCounter(oldRoom);
      console.log(`Removed element from old room: ${oldRoomName}`);
    }
  }

  function addToNewRoom(el, newRoom) {
    newRoom.objects.push(el);
    el.dataset.room = newRoom.el.dataset.name;
    updateCounter(newRoom);
    console.log(`Added element to new room: ${newRoom.el.dataset.name}`);
  }

  function stopDragging() {
    if (!dragging) return;
    dragging = false;
    el.style.cursor = "grab";
    console.log("Dragging stopped");

    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);

    const foundRoom = findRoomContainingElementCenter(el);

    if (foundRoom) {
      if (el.dataset.room !== foundRoom.el.dataset.name) {
        removeFromOldRoom(el);
        addToNewRoom(el, foundRoom);
      }

      snapObjectToZone(el, foundRoom);
      updateZIndex(el, foundRoom);
      console.log("Snapped to new room zone and updated z-index");
    } else {
      if (rooms[el.dataset.room]) {
        snapObjectToZone(el, rooms[el.dataset.room]);
        console.log("Snapped back to old room zone");
      }
    }
  }

  function onMouseUp(ev) {
    stopDragging();
  }

  el.addEventListener("mousedown", startDragging);
}

// UI - Objekt hinzufügen
const addBtn = document.getElementById("addBtn");
const shapeSelector = document.getElementById("shapeSelector");
const shapeSelect = document.getElementById("shapeSelect");
const confirmAddBtn = document.getElementById("confirmAddBtn");

addBtn.addEventListener("click", () => {
  shapeSelector.style.display = "block";
});
confirmAddBtn.addEventListener("click", () => {
  selectedShape = shapeSelect.value;
  createObject(selectedShape);
  shapeSelector.style.display = "none";
});

floorplan.style.transformOrigin = "0 0";

floorplan.addEventListener("mousedown", e => {
  if (e.target.classList.contains("object")) return; // Nur auf Floorplan, nicht Objekte

  isPanning = true;
  startPanX = e.clientX;
  startPanY = e.clientY;
  startOffsetX = offsetX;
  startOffsetY = offsetY;
  floorplan.style.cursor = "grabbing";
});

window.addEventListener("mouseup", e => {
  isPanning = false;
  floorplan.style.cursor = "grab";
});

window.addEventListener("mousemove", e => {
  if (!isPanning) return;
  const dx = e.clientX - startPanX;
  const dy = e.clientY - startPanY;
  offsetX = startOffsetX + dx;
  offsetY = startOffsetY + dy;
  applyTransform();
});

floorplan.addEventListener("wheel", e => {
  e.preventDefault();

  // Zoom um Mausposition
  const zoomIntensity = 0.1;
  const oldScale = scale;
  if (e.deltaY < 0) {
    scale *= 1 + zoomIntensity;
  } else {
    scale /= 1 + zoomIntensity;
  }
  scale = Math.min(Math.max(0.5, scale), 3);

  // Berechne Offset, damit Zoom um Mausposition erfolgt
  const floorplanRect = floorplan.getBoundingClientRect();
  const mx = e.clientX - floorplanRect.left;
  const my = e.clientY - floorplanRect.top;

  offsetX -= (mx / oldScale - mx / scale);
  offsetY -= (my / oldScale - my / scale);

  applyTransform();
}, { passive: false });

function applyTransform() {
  floorplan.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
}

// Initial
applyTransform();
createRooms();