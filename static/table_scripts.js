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

// Delete-Funktion
$(".delete-entry").on("click", function() {
	const $row = $(this).closest("tr");
	// Annahme: ID steht im data-id Attribut des <tr>
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
