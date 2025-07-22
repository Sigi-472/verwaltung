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

$(document).on("click", ".delete-entry", function () {
	const name = $(this).data("rowname");
	$.post("/delete/{{ table_name }}", { name: name })
		.done(function (resp) {
			if (resp.success) {
				toastr.success("Eintrag gelöscht.");
				location.reload();
			} else {
				toastr.error("Fehler beim Löschen: " + (resp.error || "Unbekannter Fehler"));
			}
		})
		.fail(function (xhr) {
			toastr.error("Serverfehler: " + xhr.statusText);
		});
});

$(function() {
    // Initialisiere Autocomplete für alle Eingabefelder mit data-autocomplete
    $(".cell-input").each(function() {
        var input = $(this);
        var data = input.data("autocomplete"); // Erwarte Array: [{label:"aaaa (2)", value:"2"}, ...]

        if (data) {
            input.autocomplete({
                source: data,
                minLength: 0,
                delay: 0,
                autoFocus: true,
                select: function(event, ui) {
                    // ui.item.label = sichtbarer Text, ui.item.value = ID
                    input.val(ui.item.label);          // sichtbarer Wert bleibt der Text mit z.B. "aaaa (2)"
                    input.attr("data-id", ui.item.value); // ID im data-id Attribut speichern (z.B. "2")
                    input.trigger("change");           // change-Event manuell triggern, um speichern anzustoßen
                    return false;                      // Verhindert Default-Eintrag
                }
            }).focus(function() {
                // autocomplete direkt beim Fokus anzeigen
                $(this).autocomplete("search", "");
            });
        }
    });

    // Wenn ein Feld geändert wird, sende das update an den Server
    $(".cell-input").filter(function() {
        // Nur Felder, die nicht in neuen Zeilen sind
        return $(this).closest(".new-entry").length === 0;
    }).on("change", function() {
        var input = $(this);
        var name = input.attr("name");

        // Versuche data-id auszulesen
        var dataId = input.attr("data-id");

        // Debug: Prüfe was gesendet wird
        console.log("DEBUG: Feld:", name, "data-id:", dataId, "input value:", input.val());

        // Sende die ID, wenn vorhanden, sonst den sichtbaren Wert
        var valueToSend = (typeof dataId !== "undefined" && dataId !== "") ? dataId : input.val();

        $.post("/update/{{ table_name }}", { name: name, value: valueToSend }, function(resp) {
            if (!resp.success) {
                toastr.error("Fehler beim Updaten: " + resp.error);
            } else {
                toastr.success("Eintrag geupdatet");
                // Optional: Nach erfolgreichem Speichern data-id entfernen, wenn du willst:
                // input.removeAttr("data-id");
            }
        }, "json").fail(function() {
            toastr.error("Netzwerkfehler beim Updaten");
        });
    });
});
