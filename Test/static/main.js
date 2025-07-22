  const floorplan = document.getElementById("floorplan");
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let objId = 0;
  let selectedShape = null;

  // Räume
  const roomsData = [
    { name: "701", x: 0, y: 0 },
    { name: "703", x: 220, y: 0 },
    { name: "705", x: 440, y: 0 },
    { name: "707", x: 660, y: 0 },
    { name: "709", x: 880, y: 0 },
    { name: "711", x: 0, y: 180 },
    { name: "713", x: 220, y: 180 },
    { name: "715", x: 440, y: 180 },
    { name: "717", x: 660, y: 180 },
    { name: "719", x: 880, y: 180 },
  ];
  const rooms = {};

  // Räume + Snapzones erzeugen
  function createRooms() {
    roomsData.forEach(data => {
      const room = document.createElement("div");
      room.className = "room";
      room.style.left = data.x + "px";
      room.style.top = data.y + "px";
      room.dataset.name = data.name;

      const label = document.createElement("div");
      label.className = "room-label";
      label.textContent = "Raum " + data.name;

      const counter = document.createElement("div");
      counter.className = "room-counter";
      counter.textContent = "0 Objekt(e)";
      counter.dataset.count = "0";

      // Snapzone Laptop (kleiner)
      const snapLaptop = document.createElement("div");
      snapLaptop.className = "snapzone laptop";
      snapLaptop.dataset.shape = "laptop";

      // Snapzone Stuhl (kleiner)
      const snapStuhl = document.createElement("div");
      snapStuhl.className = "snapzone stuhl";
      snapStuhl.dataset.shape = "stuhl";

      room.appendChild(label);
      room.appendChild(counter);
      room.appendChild(snapLaptop);
      room.appendChild(snapStuhl);
      floorplan.appendChild(room);

      rooms[data.name] = {
        el: room,
        counterEl: counter,
        snapzones: {
          laptop: snapLaptop,
          stuhl: snapStuhl,
        },
        objects: []
      };
    });
  }
  createRooms();

  // Bildquellen
  const shapeImages = {
    laptop: "/static/Laptop_Bild.png",
    stuhl: "/static/Stuhl_Bild.png"
  };

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

  // Prüft, ob Snapzone belegt ist
  function isSnapzoneOccupied(room, shape) {
    return room.objects.some(obj => obj.dataset.snapped === "true" && obj.dataset.shape === shape);
  }

  // Snappen in die richtige Snapzone des Raumes, wenn frei
  function snapObjectToZone(el, room) {
    const shape = el.dataset.shape;
    const snapzone = room.snapzones[shape];
    if (!snapzone) return;

    // Prüfe ob die Snapzone bereits belegt ist (max 1 Objekt pro Snapzone)
    if (isSnapzoneOccupied(room, shape) && el.dataset.snapped !== "true") {
      // Snapzone belegt, Objekt bleibt wo es ist
      el.dataset.snapped = "false";
      return;
    }

    const floorplanRect = floorplan.getBoundingClientRect();
    const snapRect = snapzone.getBoundingClientRect();

    // Berechne Position relativ zum Floorplan (und berücksichtigt Scale)
    let left = (snapRect.left - floorplanRect.left) / scale + (snapzone.offsetWidth - el.offsetWidth) / 2;
    let top = (snapRect.top - floorplanRect.top) / scale + (snapzone.offsetHeight - el.offsetHeight) / 2;

    el.style.left = left + "px";
    el.style.top = top + "px";

    el.dataset.snapped = "true";
  }

  function updateZIndex(obj, room) {
    obj.style.zIndex = 300;
  }

  // Draggable mit mittigem Greifen
  function makeDraggable(el) {
    let dragging = false;
    let dragOffsetX = 0;
    let dragOffsetY = 0;

    el.addEventListener("mousedown", (e) => {
      e.preventDefault();
      dragging = true;
      el.style.cursor = "grabbing";

      const elRect = el.getBoundingClientRect();

      // Offset von Mausposition zur Elementmitte
      dragOffsetX = e.clientX - (elRect.left + elRect.width / 2);
      dragOffsetY = e.clientY - (elRect.top + elRect.height / 2);

      function onMouseMove(ev) {
        if (!dragging) return;

        const floorplanRect = floorplan.getBoundingClientRect();

        // Mausposition relativ zum Floorplan, korrigiert um Offset
        let mouseX = ev.clientX - floorplanRect.left - el.offsetWidth / 2 - dragOffsetX;
        let mouseY = ev.clientY - floorplanRect.top - el.offsetHeight / 2 - dragOffsetY;

        // Auf Koordinatensystem skalieren
        let x = mouseX / scale;
        let y = mouseY / scale;

        // Begrenze innerhalb Floorplan-Größe
        x = Math.min(Math.max(0, x), floorplan.offsetWidth - el.offsetWidth);
        y = Math.min(Math.max(0, y), floorplan.offsetHeight - el.offsetHeight);

        el.style.left = x + "px";
        el.style.top = y + "px";
        el.dataset.snapped = "false";
      }

      function onMouseUp(ev) {
        if (!dragging) return;
        dragging = false;
        el.style.cursor = "grab";
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);

        let foundRoom = null;
        Object.values(rooms).forEach(room => {
          const rRect = room.el.getBoundingClientRect();
          const objRect = el.getBoundingClientRect();
          const cx = objRect.left + objRect.width / 2;
          const cy = objRect.top + objRect.height / 2;

          if (cx > rRect.left && cx < rRect.right && cy > rRect.top && cy < rRect.bottom) {
            foundRoom = room;
          }
        });

        if (foundRoom) {
          if (el.dataset.room !== foundRoom.el.dataset.name) {
            if (rooms[el.dataset.room]) {
              const oldRoom = rooms[el.dataset.room];
              oldRoom.objects = oldRoom.objects.filter(o => o !== el);
              updateCounter(oldRoom);
            }

            foundRoom.objects.push(el);
            el.dataset.room = foundRoom.el.dataset.name;
            updateCounter(foundRoom);
          }

          snapObjectToZone(el, foundRoom);
          updateZIndex(el, foundRoom);
        } else {
          // Objekt fällt raus, snappt zurück in alten Raum, falls vorhanden
          if (rooms[el.dataset.room]) {
            snapObjectToZone(el, rooms[el.dataset.room]);
          }
        }
      }

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    });
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

  // Zoom & Pan im Floorplan aktivieren
  let isPanning = false;
  let startPanX = 0;
  let startPanY = 0;
  let startOffsetX = 0;
  let startOffsetY = 0;

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
