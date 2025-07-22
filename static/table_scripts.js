// Toastr Optionen (deine bestehende Konfiguration)
toastr.options = {
	"closeButton": true,
	"debug": false,
	"newestOnTop": true,
	"progressBar": true,
	"positionClass": "toast-top-right",
	"preventDuplicates": true,
	"showDuration": "300",
	"hideDuration": "1000",
	"timeOut": "3500",
	"extendedTimeOut": "1000",
	"showEasing": "swing",
	"hideEasing": "linear",
	"showMethod": "fadeIn",
	"hideMethod": "fadeOut"
};

// Funktion, die prüft, ob mindestens ein Feld in der neuen Zeile gefüllt ist
function checkNewEntryInputs() {
	const inputs = $(".new-entry input, .new-entry select");
	let isAnyFilled = false;

	inputs.each(function() {
		// Wert holen, trimmen (für Strings)
		let value = $(this).val();
		if (typeof value === "string") {
			value = value.trim();
		}
		// Falls Wert nicht leer, dann Button aktivieren
		if (value !== "" && value !== null && value !== undefined) {
			isAnyFilled = true;
			return false; // Schleife abbrechen, da erfüllt
		}
	});

	$(".save-new").prop("disabled", !isAnyFilled);
}

// Beim Laden der Seite Button deaktivieren
$(document).ready(function() {
	// Button per default deaktivieren
	$(".save-new").prop("disabled", true);

	// Bei Änderung der Inputs prüfen
	$(".new-entry input, .new-entry select").on("input change", function() {
		checkNewEntryInputs();
	});
});

// Bestehender Update-Code für vorhandene Einträge (unverändert)
$(".cell-input").filter(function() {
	return $(this).closest(".new-entry").length === 0;
}).on("change", function() {
	const name = $(this).attr("name");
	const value = $(this).val();
	$.post("/update/{{ table_name }}", { name, value }, function(resp) {
		if (!resp.success) {
			toastr.error("Fehler beim Updaten: " + resp.error);
		} else {
			toastr.success("Eintrag geupdatet");
		}
	}, "json").fail(function() {
		toastr.error("Netzwerkfehler beim Updaten");
	});
});

// Speichern neuer Eintrag
$(".save-new").on("click", function() {
	const data = {};
	$(".new-entry input, .new-entry select").each(function() {
		data[$(this).attr("name")] = $(this).val();
	});
	$.post("/add/{{ table_name }}", data, function(resp) {
		if (!resp.success) {
			toastr.error("Fehler beim Speichern: " + resp.error);
		} else {
			toastr.success("Eintrag gespeichert");
			location.reload();
		}
	}, "json").fail(function() {
		toastr.error("Netzwerkfehler beim Speichern");
	});
});

// Löschen Eintrag
$(".delete-entry").on("click", function() {
	const $row = $(this).closest("tr");
	const id = $row.data("id");

	if (id === null || id === undefined) {
		toastr.error(`Datensatz-ID nicht gefunden: ${id}.`);
		return;
	}

	if (!confirm("Soll dieser Eintrag wirklich gelöscht werden?")) {
		return;
	}

	$.ajax({
		url: "/delete/{{ table_name }}",
		method: "POST",
		contentType: "application/json",
		data: JSON.stringify({ id: id }),
		dataType: "json"
	}).done(function(resp) {
		if (!resp.success) {
			toastr.error("Fehler beim Löschen: " + resp.error);
		} else {
			toastr.success("Eintrag gelöscht");
			$row.remove();
		}
	}).fail(function() {
		toastr.error("Netzwerkfehler beim Löschen");
	});
});
