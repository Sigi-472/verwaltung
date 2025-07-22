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
    $(".cell-input").filter(function() {
        return $(this).closest(".new-entry").length === 0;
    }).on("change", function() {
        const input = $(this);
        const name = input.attr("name");

        // Prüfe, ob ein Autocomplete-Wert gewählt wurde
        const dataId = input.attr("data-id");
        const value = (typeof dataId !== "undefined" && dataId !== "") ? dataId : input.val();

        $.post("/update/{{ table_name }}", { name, value }, function(resp) {
            if (!resp.success) {
                toastr.error("Fehler beim Updaten: " + resp.error);
            } else {
                toastr.success("Eintrag geupdatet");
            }
        }, "json").fail(function() {
            toastr.error("Netzwerkfehler beim Updaten");
        });

        // Leere data-id nach Versand, um versehentliche Wiederverwendung zu vermeiden
        input.removeAttr("data-id");
    });

    // Initialisiere Autocomplete
    $(".cell-input").each(function() {
        var input = $(this);
        var data = input.data("autocomplete");
        if (data) {
            input.autocomplete({
                source: data,
                minLength: 0,
                delay: 0,
                autoFocus: true,
                select: function(event, ui) {
                    input.val(ui.item.label);         // Zeige den Namen im Feld
                    input.attr("data-id", ui.item.value); // Speichere die ID
                    input.trigger("change");          // Löst sofort den Speichervorgang aus
                    return false;
                }
            }).focus(function() {
                $(this).autocomplete("search", "");
            });
        }
    });
});
