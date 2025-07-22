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
        var input = $(this);
        var name = input.attr("name");

        // Wert aus data-id, wenn vorhanden, sonst aus sichtbarem Text
        var dataId = input.attr("data-id");
        var value = (typeof dataId !== "undefined" && dataId !== "") ? dataId : input.val();

        $.post("/update/{{ table_name }}", { name: name, value: value }, function(resp) {
            if (!resp.success) {
                toastr.error("Fehler beim Updaten: " + resp.error);
            } else {
                toastr.success("Eintrag geupdatet");
                // Nur nach Erfolg data-id entfernen, damit nicht verloren geht
                input.removeAttr("data-id");
            }
        }, "json").fail(function() {
            toastr.error("Netzwerkfehler beim Updaten");
        });
    });

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
                    // sichtbarer Text bleibt ui.item.label
                    input.val(ui.item.label);
                    // ID speichern für spätere Übertragung
                    input.attr("data-id", ui.item.value);
                    // Trigger für automatisches Speichern (change-Event)
                    input.trigger("change");
                    return false;
                }
            }).focus(function() {
                $(this).autocomplete("search", "");
            });
        }
    });
});
