function getCallerInfo() {
    const stack = new Error().stack;
    const callerLine = stack.split("\n")[3]?.trim() || "unknown"; // [0]=Error, [1]=getCallerInfo, [2]=log, [3]=Aufrufer
    return callerLine.replace(/^at\s+/, '');
}

const log = (...args) => {
    console.log(`[${getCallerInfo()}]`, ...args);
};

const debug = (...args) => {
    console.debug(`[${getCallerInfo()}]`, ...args);
};

const warn = (...args) => {
    console.warn(`[${getCallerInfo()}]`, ...args);
};

const error = (...args) => {
    console.error(`[${getCallerInfo()}]`, ...args);
};

// State
let rooms = [];
let currentMode = null; // 'draw-room', 'draw-snapzone', null
let drawingRoom = null;
let drawingSnapzone = null;
let selectedRoomId = null;
let dragData = null; // {type: 'room'|'snapzone', id, offsetX, offsetY, element}
let resizeData = null; // {type, id, edge, startX, startY, startWidth, startHeight}
let global_room = null;
let zoomLevel = 1;

let mauszeigerAufRoom = false;

// IDs
let roomCounter = 1;
let snapzoneCounter = 1;

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

// Helpers (jQuery-Version)
function createElement(tag, cls, parent) {
    debug(`createElement: <${tag}> mit Klasse "${cls}"`);
    const $el = $('<' + tag + '/>');
    if (cls) $el.addClass(cls);
    if (parent) {
        debug(`Element wird an Parent angehängt:`, parent);
        $(parent).append($el);
    }
    return $el[0]; // Falls du das native DOM-Element brauchst
}

function confirmDelete(msg) {
    warn(`Bestätigung erforderlich: ${msg}`);
    return window.confirm(msg);
}

function updateOutput() {
    try {
        log('updateOutput: Räume werden exportiert...');
        const exportData = rooms.map(room => {
            if (!room.snapzones) {
                warn(`Raum "${room.name}" hat keine Snapzones.`);
            }

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
                        height: Math.round(sz.height),
                        id: sz.id
                    };
                })
            };
        });

        debug('Exportierte Daten:', exportData);
        $('#output').text(JSON.stringify(exportData, null, 2));
        log('Export erfolgreich abgeschlossen.');
    } catch (e) {
        error('Fehler beim Export der Räume:', e);
    }
}
function getMousePos(evt) {
    const rect = container.getBoundingClientRect();
    const pos = {
        x: evt.clientX - rect.left,
        y: evt.clientY - rect.top
    };
    debug('getMousePos:', pos);
    return pos;
}

function isInside(a, b) {
    const result = (
        a.x >= b.x &&
        a.y >= b.y &&
        a.x + a.width <= b.x + b.width &&
        a.y + a.height <= b.y + b.height
    );
    debug('isInside:', { a, b, result });
    return result;
}

// Zeichenmodus starten
function startDrawRoom() {
    log('Zeichenmodus für Raum gestartet');
    currentMode = 'draw-room';
    $('#draw-room-btn').prop('disabled', true);
    $('#draw-snapzone-btn').prop('disabled', true);
    $('#snapzone-type-select').prop('disabled', true);
    $('#cancel-draw-btn').prop('disabled', false);
    $('#container').css('cursor', 'crosshair');
}

function startDrawSnapzone() {
    if (selectedRoomId === null) {
        warn('Snapzone-Zeichnung gestartet, aber kein Raum ist ausgewählt');
        alert('Bitte zuerst einen Raum auswählen.');
        return;
    }
    log('Zeichenmodus für Snapzone gestartet');
    currentMode = 'draw-snapzone';
    $('#draw-room-btn').prop('disabled', true);
    $('#draw-snapzone-btn').prop('disabled', true);
    $('#snapzone-type-select').prop('disabled', false);
    $('#cancel-draw-btn').prop('disabled', false);
    $('#container').css('cursor', 'crosshair');
}

function cancelDraw() {
    log('Zeichnung abgebrochen');
    currentMode = null;
    drawingRoom = null;
    drawingSnapzone = null;
    $('#draw-room-btn').prop('disabled', false);
    $('#draw-snapzone-btn').prop('disabled', selectedRoomId === null);
    $('#snapzone-type-select').prop('disabled', selectedRoomId === null);
    $('#cancel-draw-btn').prop('disabled', true);
    $('#container').css('cursor', 'default');
    renderAll();
}


function delete_room_or_snapzone(e, ask = true, this_room = global_room) {
    if(e !== undefined && e !== null) {
        e.stopPropagation();
    }

    if (ask && confirmDelete(`Raum "${this_room.name || this_room.id}" löschen?`) || ask == false) {
        warn(`Raum gelöscht: ${this_room.name || this_room.id}`);
        rooms = rooms.filter(r => r.id !== this_room.id);
        if (selectedRoomId === this_room.id) {
            selectedRoomId = null;
            $('#draw-snapzone-btn').prop('disabled', true);
            $('#snapzone-type-select').prop('disabled', true);
        }

        updateOutput();
        renderAll();
    } else{
        log(`NOT DELETING: ${room}`)
    }
}

// Raum erstellen
function createRoomElement(room) {
    log(`Raum-Element wird erstellt:`, room);
    const $el = $('<div class="room"></div>').appendTo($('#container'));
    $el.css({
        left: room.x + 'px',
        top: room.y + 'px',
        width: room.width + 'px',
        height: room.height + 'px',
        borderColor: (selectedRoomId === room.id)
            ? 'rgba(0,0,255,0.9)'
            : 'rgba(0,0,255,0.6)'
    });
    $el.attr('data-id', room.id);

    // Name-Eingabe
    const $nameInput = $('<input type="text" class="name-input" title="Raumname">')
        .val(room.name)
        .appendTo($el)
        .on('input', function () {
            room.name = $(this).val();
            debug(`Raumname geändert: ${room.name}`);
            updateOutput();
        });

    global_room = room;

    // Löschen-Button
    const $delBtn = $('<div class="delete-btn" title="Raum löschen">×</div>')
        .appendTo($el)
        .on('click', delete_room_or_snapzone);

    // Drag/Resize
    enableDragResize($el, 'room', room);
    debug('Drag/Resize für Raum aktiviert');

    // Snapzones rendern
    room.snapzones.forEach(snapzone => {
        debug(`Snapzone wird gerendert:`, snapzone);
        const szEl = createSnapzoneElement(snapzone, room);
        $el.append(szEl);
    });

    $el.on('click', function (e) {
        e.stopPropagation();
        if (selectedRoomId !== room.id) {
            log(`Raum ausgewählt: ${room.name || room.id}`);
            selectedRoomId = room.id;
            $('#draw-snapzone-btn').prop('disabled', false);
            $('#snapzone-type-select').prop('disabled', false);
            renderAll();
        }
    });

    return $el[0]; // native Element zurückgeben (für Drag)
}

var snapzoneId = 0;

function createSnapzoneElement(snapzone, room) {
    log(`Snapzone wird erstellt:`, snapzone);

    const $el = $(`<div class="snapzone" id="snapzone${snapzone.id}"></div>`)
        .css({
            left: snapzone.x + 'px',
            top: snapzone.y + 'px',
            width: snapzone.width + 'px',
            height: snapzone.height + 'px',
            borderColor: SNAPZONE_BORDER_COLORS[snapzone.type] || 'gray',
            backgroundColor: SNAPZONE_COLORS[snapzone.type] || 'rgba(0,0,0,0.1)'
        })
        .attr('data-id', snapzone.id);

    // Typ-Auswahl
    const $typeSelect = $('<select class="type-select"></select>').appendTo($el);
    ['laptop', 'stuhl', 'tisch'].forEach(type => {
        $('<option></option>')
            .val(type)
            .text(type)
            .prop('selected', type === snapzone.type)
            .appendTo($typeSelect);
    });

    $typeSelect.on('change', function () {
        const oldType = snapzone.type;
        snapzone.type = $(this).val();
        debug(`Snapzone-Typ geändert von "${oldType}" zu "${snapzone.type}"`);

        $el.css({
            borderColor: SNAPZONE_BORDER_COLORS[snapzone.type] || 'gray',
            backgroundColor: SNAPZONE_COLORS[snapzone.type] || 'rgba(0,0,0,0.1)'
        });

        updateOutput();
    });

    // Löschen-Button
    $('<div class="delete-btn" title="Snapzone löschen">×</div>')
        .appendTo($el)
        .on('click', function (e) {
            e.stopPropagation();
            if (confirmDelete(`Snapzone "${snapzone.type}" löschen?`)) {
                log(snapzone)
                const idx = room.snapzones.findIndex(sz => sz.id === snapzone.id);
                if (idx !== -1) {
                    room.snapzones.splice(idx, 1);
                    warn(`Snapzone gelöscht:`, snapzone);
                    updateOutput();
                    renderAll();
                } else {
                    error('Fehler beim Löschen: Snapzone nicht gefunden');
                }
            }
        });

    // Drag/Resize aktivieren
    enableDragResize($el, 'snapzone', snapzone, room);
    debug('Drag/Resize für Snapzone aktiviert');

    return $el[0]; // native DOM-Element zurückgeben
}

function getResizeEdge(e, rect) {
    try {
        if (!e || !rect) {
            error('getResizeEdge: Event or rect is undefined');
            return null;
        }

        const margin = 8; // Bereich in Pixeln, in dem Resize erkannt wird
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const right = rect.width;
        const bottom = rect.height;

        log(`Mouse position relative to element: x=${x}, y=${y}`);
        log(`Element size: width=${right}, height=${bottom}`);

        let edge = '';

        if (x > right - margin) {
            edge += 'r';  // rechte Kante
            log('Resize edge detected: right');
        } else if (x < margin) {
            edge += 'l';  // linke Kante
            log('Resize edge detected: left');
        }

        if (y > bottom - margin) {
            edge += 'b';  // untere Kante
            log('Resize edge detected: bottom');
        } else if (y < margin) {
            edge += 't';  // obere Kante
            log('Resize edge detected: top');
        }

        if (!edge) {
            log('No resize edge detected');
            return null;
        }

        log(`Final resize edge string: "${edge}"`);
        return edge;
    } catch (err) {
        error('Error in getResizeEdge:', err);
        return null;
    }
}
function getScaleFactor() {
    const container = document.getElementById('container');
    const style = window.getComputedStyle(container);
    const transform = style.transform || style.webkitTransform;

    if (!transform || transform === 'none') return 1;

    const match = transform.match(/^matrix\((.+)\)$/);
    if (match) {
        const values = match[1].split(', ');
        const scaleX = parseFloat(values[0]);
        return isNaN(scaleX) ? 1 : scaleX;
    }

    return 1;
}

function getMouseRelativeToContainer(event) {
    const container = document.getElementById('container');
    const rect = container.getBoundingClientRect();
    const scale = getScaleFactor();

    return {
        x: (event.clientX - rect.left) / scale,
        y: (event.clientY - rect.top) / scale
    };
}

function enableDragResize($el, type, obj, parentRoom = null) {
    $el.on('mousedown', function (e) {
        log(e);

        if (currentMode == 'draw-snapzone' && parentRoom === null) {
            warn("Not dragging because snap-zone mode was enabled");
            return;
        }

        const $target = $(e.target);
        if (
            $target.hasClass('delete-btn') ||
            $target.is('input') ||
            $target.is('select')
        ) {
            debug('Drag/Resize übersprungen wegen UI-Element-Klick');
            return;
        }

        e.preventDefault();

        const rect = this.getBoundingClientRect();
        const edge = getResizeEdge(e, rect);
        const start = getMouseRelativeToContainer(e);

        window.dragData = null;
        window.resizeData = null;

        let dragDataLocal = {
            type,
            id: obj.id,
            element: this,
            startX: start.x,
            startY: start.y,
            origX: obj.x,
            origY: obj.y,
            origWidth: obj.width,
            origHeight: obj.height,
            edge,
            parentRoom
        };

        if (edge) {
            log(`Resize gestartet (${type}): ID=${obj.id}, Edge=${edge}`);
            window.resizeData = dragDataLocal;
        } else {
            log(`Drag gestartet (${type}): ID=${obj.id}`);
            window.dragData = dragDataLocal;
        }

        $(document).on('mousemove.dragResize', function (moveEvent) {
            const pos = getMouseRelativeToContainer(moveEvent);

            if (window.dragData) {
                const dx = pos.x - window.dragData.startX;
                const dy = pos.y - window.dragData.startY;

                obj.x = window.dragData.origX + dx;
                obj.y = window.dragData.origY + dy;

                $(window.dragData.element).css({
                    left: obj.x + 'px',
                    top: obj.y + 'px'
                });

            } else if (window.resizeData) {
                const dx = pos.x - window.resizeData.startX;
                const dy = pos.y - window.resizeData.startY;

                const edge = window.resizeData.edge;

                if (edge.includes('right')) {
                    obj.width = window.resizeData.origWidth + dx;
                }
                if (edge.includes('bottom')) {
                    obj.height = window.resizeData.origHeight + dy;
                }
                if (edge.includes('left')) {
                    obj.x = window.resizeData.origX + dx;
                    obj.width = window.resizeData.origWidth - dx;
                }
                if (edge.includes('top')) {
                    obj.y = window.resizeData.origY + dy;
                    obj.height = window.resizeData.origHeight - dy;
                }

                $(window.resizeData.element).css({
                    left: obj.x + 'px',
                    top: obj.y + 'px',
                    width: obj.width + 'px',
                    height: obj.height + 'px'
                });
            }
        });

        $(document).on('mouseup.dragResize', function () {
            if (window.dragData) {
                log(`Drag beendet (${type}): ID=${window.dragData.id}`);
                window.dragData = null;
            }
            if (window.resizeData) {
                log(`Resize beendet (${type}): ID=${window.resizeData.id}`);
                window.resizeData = null;
            }
            $(document).off('.dragResize');
        });
    });
}


function cancel_drag(e) {
    if (e.key === 'Escape') {
        if (window.dragData || window.resizeData) {
            log('Drag/Resize beendet (Escape gedrückt)');
        }
        window.dragData = null;
        window.resizeData = null;
    }
}

$(document).on('keydown', cancel_drag).on('mouseup', cancel_drag);

$(window).on('mousemove', function (e) {
    if (window.dragData) {
        e.preventDefault();
        const dx = e.clientX - window.dragData.startX;
        const dy = e.clientY - window.dragData.startY;

        if (window.dragData.type === 'room') {
            // Move room
            $(window.dragData.element).css({
                left: (window.dragData.origX + dx) + 'px',
                top: (window.dragData.origY + dy) + 'px',
                width: window.dragData.origWidth + 'px',
                height: window.dragData.origHeight + 'px'
            });

            const room = rooms.find(r => r.id === window.dragData.id);
            if (room) {
                room.x = window.dragData.origX + dx;
                room.y = window.dragData.origY + dy;
                //debug(`Raum verschoben → x:${room.x}, y:${room.y}`);
            }

        } else if (window.dragData.type === 'snapzone') {
            const room = window.dragData.parentRoom;
            let newX = window.dragData.origX + dx;
            let newY = window.dragData.origY + dy;

            newX = Math.max(0, Math.min(newX, room.width - window.dragData.element.offsetWidth));
            newY = Math.max(0, Math.min(newY, room.height - window.dragData.element.offsetHeight));

            $(dragData.element).css({ left: newX + 'px', top: newY + 'px' });

            const snapzone = room.snapzones.find(sz => sz.id === window.dragData.id);
            if (snapzone) {
                snapzone.x = newX;
                snapzone.y = newY;
                debug(`Snapzone verschoben → x:${newX}, y:${newY}`);
            }
        }

    } else if (window.resizeData) {
        e.preventDefault();
        const dx = e.clientX - window.resizeData.startX;
        const dy = e.clientY - window.resizeData.startY;

        if (window.resizeData.type === 'room') {
            const room = rooms.find(r => r.id === window.resizeData.id);
            if (!room) return;

            let x = room.x;
            let y = room.y;
            let w = window.resizeData.origWidth;
            let h = window.resizeData.origHeight;

            if (window.resizeData.edge.includes('r')) w = Math.max(20, w + dx);
            if (window.resizeData.edge.includes('b')) h = Math.max(20, h + dy);
            if (window.resizeData.edge.includes('l')) {
                w = Math.max(20, w - dx);
                x = window.resizeData.origX + dx;
            }
            if (window.resizeData.edge.includes('t')) {
                h = Math.max(20, h - dy);
                y = window.resizeData.origY + dy;
            }

            x = Math.max(0, x);
            y = Math.max(0, y);
            if (x + w > container.clientWidth) w = container.clientWidth - x;
            if (y + h > container.clientHeight) h = container.clientHeight - y;

            room.x = x;
            room.y = y;
            room.width = w;
            room.height = h;

            debug(`Raum resized → x:${x}, y:${y}, w:${w}, h:${h}`);

            renderAll();
            updateOutput();

        } else if (window.resizeData.type === 'snapzone') {
            const room = window.resizeData.parentRoom;
            const snapzone = room.snapzones.find(sz => sz.id === window.resizeData.id);
            if (!snapzone) return;

            let x = snapzone.x;
            let y = snapzone.y;
            let w = window.resizeData.origWidth;
            let h = window.resizeData.origHeight;

            if (window.resizeData.edge.includes('r')) w = Math.max(10, w + dx);
            if (window.resizeData.edge.includes('b')) h = Math.max(10, h + dy);
            if (window.resizeData.edge.includes('l')) {
                w = Math.max(10, w - dx);
                x = window.resizeData.origX + dx;
            }
            if (window.resizeData.edge.includes('t')) {
                h = Math.max(10, h - dy);
                y = window.resizeData.origY + dy;
            }

            x = Math.max(0, x);
            y = Math.max(0, y);
            if (x + w > room.width) w = room.width - x;
            if (y + h > room.height) h = room.height - y;

            snapzone.x = x;
            snapzone.y = y;
            snapzone.width = w;
            snapzone.height = h;

            debug(`Snapzone resized → x:${x}, y:${y}, w:${w}, h:${h}`);

            renderAll();
            updateOutput();
        }
    }
});
// Drawing new rooms and snapzones (mousedown)
$(container).on('mousedown', function (e) {
    if (currentMode === 'draw-room') {
        const pos = getMousePos(e);
        drawingRoom = { x: pos.x, y: pos.y, width: 0, height: 0 };
        log(`Start drawing room at (${pos.x}, ${pos.y})`);
        drawTempRect('room', drawingRoom);

    } else if (currentMode === 'draw-snapzone') {
        if (selectedRoomId === null) {
            error('Kein Raum ausgewählt – Snapzone kann nicht gezeichnet werden.');
            return;
        }
        const room = rooms.find(r => r.id === selectedRoomId);
        const pos = getMousePos(e);
        const relX = pos.x - room.x;
        const relY = pos.y - room.y;
        if (relX < 0 || relY < 0 || relX > room.width || relY > room.height) {
            warn('Maus außerhalb des Raums – Snapzone kann hier nicht gestartet werden.');
            return;
        }

        drawingSnapzone = {
            x: relX,
            y: relY,
            width: 0,
            height: 0,
            type: $('#snapzone-type-select').val()
        };
        log(`Start drawing snapzone of type "${drawingSnapzone.type}" at relative position (${relX}, ${relY}) in Raum ${selectedRoomId}`);
        drawTempRect('snapzone', drawingSnapzone, room);
    }
});

// Mousemove for drawing
$(container).on('mousemove', function (e) {
    if (currentMode === 'draw-room' && drawingRoom) {
        const pos = getMousePos(e);
        drawingRoom.width = Math.max(1, pos.x - drawingRoom.x);
        drawingRoom.height = Math.max(1, pos.y - drawingRoom.y);
        debug(`Drawing room resize to width: ${drawingRoom.width}, height: ${drawingRoom.height}`);
        drawTempRect('room', drawingRoom);

    } else if (currentMode === 'draw-snapzone' && drawingSnapzone) {
        const room = rooms.find(r => r.id === selectedRoomId);
        const pos = getMousePos(e);
        let w = pos.x - room.x - drawingSnapzone.x;
        let h = pos.y - room.y - drawingSnapzone.y;
        w = Math.max(1, w);
        h = Math.max(1, h);

        if (drawingSnapzone.x + w > room.width) {
            w = room.width - drawingSnapzone.x;
            warn('Snapzone Breite wird auf Raumgrenze beschränkt.');
        }
        if (drawingSnapzone.y + h > room.height) {
            h = room.height - drawingSnapzone.y;
            warn('Snapzone Höhe wird auf Raumgrenze beschränkt.');
        }

        drawingSnapzone.width = w;
        drawingSnapzone.height = h;
        debug(`Drawing snapzone resize to width: ${w}, height: ${h}`);
        drawTempRect('snapzone', drawingSnapzone, room);
    }
});

// Mouseup to finalize drawing
$(window).on('mouseup', function (e) {
    if (currentMode === 'draw-room' && drawingRoom) {
        if (drawingRoom.width > 5 && drawingRoom.height > 5) {
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
            log(`Neuer Raum erstellt: ID=${newRoom.id}, Position=(${newRoom.x},${newRoom.y}), Größe=(${newRoom.width}x${newRoom.height})`);
            $('#draw-snapzone-btn').prop('disabled', false);
            $('#snapzone-type-select').prop('disabled', false);
        } else {
            warn('Gezeichneter Raum zu klein, wird ignoriert.');
        }

        drawingRoom = null;
        currentMode = null;
        $('#draw-room-btn').prop('disabled', false);
        $('#draw-snapzone-btn').prop('disabled', selectedRoomId === null);
        $('#snapzone-type-select').prop('disabled', selectedRoomId === null);
        $('#cancel-draw-btn').prop('disabled', true);
        removeTempRects();
        renderAll();
        updateOutput();

    } else if (currentMode === 'draw-snapzone' && drawingSnapzone) {
        if (drawingSnapzone.width > 5 && drawingSnapzone.height > 5) {
            const room = rooms.find(r => r.id === selectedRoomId);
            if (room) {
                room.snapzones.push({
                    id: `snapzone${snapzoneCounter++}`,
                    type: drawingSnapzone.type,
                    x: drawingSnapzone.x,
                    y: drawingSnapzone.y,
                    width: drawingSnapzone.width,
                    height: drawingSnapzone.height
                });
                log(`Neue Snapzone erstellt: ID=sz${snapzoneCounter - 1}, Typ=${drawingSnapzone.type}, Position=(${drawingSnapzone.x},${drawingSnapzone.y}), Größe=(${drawingSnapzone.width}x${drawingSnapzone.height}) in Raum ${selectedRoomId}`);
            } else {
                error('Raum für Snapzone nicht gefunden.');
            }
        } else {
            warn('Gezeichnete Snapzone zu klein, wird ignoriert.');
        }

        drawingSnapzone = null;
        currentMode = null;
        $('#draw-room-btn').prop('disabled', false);
        $('#draw-snapzone-btn').prop('disabled', selectedRoomId === null);
        $('#snapzone-type-select').prop('disabled', selectedRoomId === null);
        $('#cancel-draw-btn').prop('disabled', true);
        removeTempRects();
        renderAll();
        updateOutput();
    }
}); function drawTempRect(type, rect, parentRoom = null) {
    log(`drawTempRect called for type "${type}" with rect:`, rect, parentRoom ? `in room ${parentRoom.id}` : 'in container');
    removeTempRects();

    const temp = createElement('div', type === 'room' ? 'room' : 'snapzone', parentRoom ? null : container);

    if (parentRoom) {
        // Erst Element mit id suchen
        let parentEl = document.getElementById(parentRoom.id);

        // Falls nicht gefunden, Element mit data-id suchen
        if (!parentEl) {
            parentEl = document.querySelector(`[data-id="${parentRoom.id}"]`);
        }

        if (!parentEl) {
            error(`Parent room element mit id oder data-id "${parentRoom.id}" nicht gefunden! Temp rect kann nicht angehängt werden.`);
            return;
        }

        parentEl.appendChild(temp);
        debug(`Temp ${type} rect angehängt an Raum ${parentRoom.id}`);
    } else {
        debug(`Temp ${type} rect angehängt an Container`);
    }

    $(temp).css({
        left: rect.x + 'px',
        top: rect.y + 'px',
        width: rect.width + 'px',
        height: rect.height + 'px',
        borderColor: type === 'room' ? 'rgba(0,0,255,0.8)' : (SNAPZONE_BORDER_COLORS[rect.type] || 'gray'),
        backgroundColor: type === 'room' ? 'rgba(0,0,255,0.3)' : (SNAPZONE_COLORS[rect.type] || 'rgba(0,0,0,0.1)')
    }).attr('id', 'temp-' + type);

    debug(`Temp ${type} rect gestylt und id "temp-${type}" gesetzt.`);
}

function removeTempRects() {
    ['temp-room', 'temp-snapzone'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
            log(`Temp rect mit id "${id}" entfernt.`);
        } else {
            debug(`Kein Temp rect mit id "${id}" zum Entfernen gefunden.`);
        }
    });
}

function renderAll() {
    log('renderAll: Container-Inhalt wird gelöscht und alle Räume neu gerendert.');
    container.innerHTML = '';

    if (!rooms || rooms.length === 0) {
        warn('Keine Räume vorhanden zum rendern.');
    }

    rooms.forEach(room => {
        const el = createRoomElement(room);
        if (!el) {
            error(`createRoomElement hat für Raum mit id ${room.id} kein Element zurückgegeben.`);
            return;
        }
        container.appendChild(el);
        debug(`Raum mit id ${room.id} zum Container hinzugefügt.`);
    });

    updateOutput();
    log('renderAll: updateOutput aufgerufen.');
}

// Initial
drawRoomBtn.addEventListener('click', () => {
    log('drawRoomBtn geklickt: Starte Zeichenmodus Raum.');
    startDrawRoom();
});
drawSnapzoneBtn.addEventListener('click', () => {
    log('drawSnapzoneBtn geklickt: Starte Zeichenmodus Snapzone.');
    startDrawSnapzone();
});
cancelDrawBtn.addEventListener('click', () => {
    log('cancelDrawBtn geklickt: Zeichenvorgang abbrechen.');
    cancelDraw();
});

// Deselect room on container click
container.addEventListener('click', e => {
    log('Container geklickt: Ausgewählten Raum abwählen.');
    selectedRoomId = null;
    drawSnapzoneBtn.disabled = true;
    snapzoneTypeSelect.disabled = true;
    renderAll();
});

function import_text() {
    if (!$("#import").length) {
        error("#import element nicht gefunden");
        return;
    }

    var text = $("#import").val()

    if (text.match(/^\s*$/)) {
        error("#import: textfeld ist leer oder besteht nur aus leerzeichen");
        return;
    }

    var parsed = null;

    try {
        parsed = JSON.parse(text);
    } catch (e) {
        error(`import_text: error parsing ${text}: ${e}`);
        return;
    }

    for (var i = 0; i < parsed.length; i++) {
        var this_room = parsed[i];

        if(rooms.some(room => room.name === this_room.name)) {
            delete_room_or_snapzone(null, false, this_room);

            document.querySelectorAll('.room').forEach(roomEl => {
                const input = roomEl.querySelector('.name-input');
                if (input && input.value === this_room.name) {
                    roomEl.remove();
                    log("removing:", this_room.name, roomEl);
                }
            });

            rooms = rooms.filter(room => room.name !== this_room.name);
        }

        drawingRoom = {
            x: this_room.x,
            y: this_room.y,
            width: this_room.width,
            height: this_room.height
        };

        log(`Start drawing room at (${this_room.x}, ${this_room.y}) with width = ${this_room.width} and height = ${this_room.height}`);
        drawTempRect('room', drawingRoom);

        const newRoom = {
            id: `r${i + 1}`,
            name: this_room.name,
            x: this_room.x,
            y: this_room.y,
            width: this_room.width,
            height: this_room.height,
            snapzones: this_room.snapzones
        };

        rooms.push(newRoom);

        removeTempRects();
        renderAll();
        updateOutput();
    }
}


function enablePageZoomWithMouseWheel() {
  const zoomStep = 0.1;
  const minZoom = 0.5;
  const maxZoom = 3;

  window.addEventListener('wheel', (event) => {
    event.preventDefault();

    if (event.deltaY < 0) {
      zoomLevel += zoomStep;
    } else {
      zoomLevel -= zoomStep;
    }
    zoomLevel = Math.min(maxZoom, Math.max(minZoom, zoomLevel));

    $("#container").css("scale", zoomLevel);
  }, { passive: false });
}


function disableMouseWheelScrollAllowArrowKeys() {
  window.addEventListener('wheel', (event) => {
    event.preventDefault(); // Mausrad-Scrollen verhindern
  }, { passive: false });

  // Pfeiltasten bleiben unberührt und können scrollen
}

document.addEventListener('mousemove', (event) => {
  const element = document.elementFromPoint(event.clientX, event.clientY);
  if (!element) {
    mauszeigerAufRoom = false;
    return;
  }
  // Prüfen, ob element oder ein Elternteil die Klasse 'room' hat
  mauszeigerAufRoom = element.closest('.room') !== null;
});

function mauszeiger_is_on_room() {
  return mauszeigerAufRoom;
}


function isMouseOutsideRooms(event, container, rooms) {
  const containerRect = container.getBoundingClientRect();
  const mouseX = event.clientX - containerRect.left;
  const mouseY = event.clientY - containerRect.top;

  for (const room of rooms) {
    const inRoom =
      mouseX >= room.x &&
      mouseX <= room.x + room.width &&
      mouseY >= room.y &&
      mouseY <= room.y + room.height;

    if (inRoom) return false; // Maus ist in einem Raum
  }

  return true; // Maus ist außerhalb aller Räume
}

function enableDragIfOutsideRooms(containerId, rooms) {
    if (window.dragData || window.resizeData) {
            log('Drag/Resize beendet (Escape gedrückt)');
        }
    window.dragData = null;
    window.resizeData = null;
  const container = document.getElementById(containerId);
  if (!container) {
    error('Element #' + containerId + ' nicht gefunden!');
    return;
  }
  
  let isDragging = false;
  let startX, startY;
  let origX = 0, origY = 0;

  container.style.position = container.style.position || 'relative';

  container.addEventListener('mousedown', (event) => {
    if (event.button !== 0) return; // Nur linke Maustaste

    if (!isMouseOutsideRooms(event, container, rooms)) {
      log('Klick war in einem Raum – Drag nicht erlaubt.');
      return;
    }

    log('Drag gestartet außerhalb der Räume');

    isDragging = true;
    startX = event.clientX;
    startY = event.clientY;

    const style = window.getComputedStyle(container);
    origX = parseInt(style.left) || 0;
    origY = parseInt(style.top) || 0;

    event.preventDefault();
  });

  window.addEventListener('mousemove', (event) => {
    if(mauszeiger_is_on_room()) {
        return;
    }
    if (!isDragging) return;

    const dx = event.clientX - startX;
    const dy = event.clientY - startY;

    container.style.left = origX + dx + 'px';
    container.style.top = origY + dy + 'px';
  });

  window.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      log('Drag beendet');
    }
  });
}

//enableDragIfOutsideRooms('container', rooms);
renderAll();
updateOutput();
//enablePageZoomWithMouseWheel()
//disableMouseWheelScrollAllowArrowKeys()
import_text();