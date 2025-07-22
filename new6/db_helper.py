# flask_html_generator.py

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy import ForeignKey, DateTime, Date, Integer, Float, String, Text
from markupsafe import escape
import html


def generate_admin_html(Base, session, header_labels=None):
    """
    Generates full HTML admin interface for all SQLAlchemy models registered with `Base`.
    
    :param Base: SQLAlchemy declarative base
    :param session: SQLAlchemy session
    :param header_labels: Optional dict in format { "table.column": "Nice Label" }
    :return: str (HTML)
    """

    def column_label(col):
        key = f"{table_name}.{col.name}"
        return header_labels.get(key, col.name.replace('_id', '').replace('_', ' ').capitalize())

    def get_input(col, value=None, row_id=None, fk_options=None):
        input_name = f"{table_name}_{row_id or 'new'}_{col.name}"
        val = "" if value is None else html.escape(str(value))

        if col.foreign_keys:
            opts = "".join(f'<option value="{o[0]}" {"selected" if o[0]==value else ""}>{escape(str(o[1]))}</option>'
                           for o in fk_options)
            return f'<select name="{input_name}" class="cell-input">{opts}</select>'

        coltype = str(col.type)
        if isinstance(col.type, (String, Text)):
            return f'<input type="text" name="{input_name}" class="cell-input" value="{val}">'
        if isinstance(col.type, Integer):
            return f'<input type="number" step="1" name="{input_name}" class="cell-input" value="{val}">'
        if isinstance(col.type, Float):
            return f'<input type="number" step="any" name="{input_name}" class="cell-input" value="{val}">'
        if isinstance(col.type, DateTime):
            return f'<input type="datetime-local" name="{input_name}" class="cell-input" value="{val}">'
        if isinstance(col.type, Date):
            return f'<input type="date" name="{input_name}" class="cell-input" value="{val}">'
        return f'<input type="text" name="{input_name}" class="cell-input" value="{val}">'

    html_parts = ['<div class="admin-ui">']
    for cls in Base.__subclasses__():
        table_name = cls.__tablename__
        mapper = class_mapper(cls)
        columns = [prop for prop in mapper.iterate_properties if isinstance(prop, ColumnProperty)]

        fk_map = {}
        fk_columns = [c for c in columns if c.columns[0].foreign_keys]
        for col in fk_columns:
            fk = list(col.columns[0].foreign_keys)[0]
            ref_table = fk.column.table.name
            ref_cls = next((c for c in Base.__subclasses__() if c.__tablename__ == ref_table), None)
            if ref_cls:
                fk_map[col.key] = [(getattr(r, fk.column.name), str(r)) for r in session.query(ref_cls).all()]

        rows = session.query(cls).all()
        html_parts.append(f'<h2>{table_name.capitalize()}</h2>')
        html_parts.append('<table class="edit-table"><thead><tr>')

        for col in columns:
            if col.columns[0].primary_key:
                continue
            label = column_label(col.columns[0])
            header = f'<th>{escape(label)}'
            if col.key in fk_map:
                header += f' <a href="#add_{col.key}" class="add-fk-link">[+]</a>'
            header += '</th>'
            html_parts.append(header)
        html_parts.append('</tr></thead><tbody>')

        for row in rows:
            html_parts.append('<tr>')
            for col in columns:
                if col.columns[0].primary_key:
                    continue
                value = getattr(row, col.key)
                fk_opts = fk_map.get(col.key)
                html_parts.append(f'<td>{get_input(col.columns[0], value, row_id=row.id, fk_options=fk_opts)}</td>')
            html_parts.append('</tr>')

        # Add empty row for new entry
        html_parts.append('<tr class="new-entry">')
        for col in columns:
            if col.columns[0].primary_key:
                continue
            fk_opts = fk_map.get(col.key)
            html_parts.append(f'<td>{get_input(col.columns[0], None, row_id=None, fk_options=fk_opts)}</td>')
        html_parts.append('<td><button class="save-new">Save</button></td>')
        html_parts.append('</tr>')

        html_parts.append('</tbody></table>')

    html_parts.append("""
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://code.jquery.com/ui/1.13.2/jquery-ui.min.js"></script>
    <script>
    $(function() {
        $(".edit-table input, .edit-table select").on("change", function() {
            const input = $(this);
            const name = input.attr("name");
            const value = input.val();
            $.post("/update", { name, value }, function(resp) {
                if (!resp.success) alert("Error: " + resp.error);
            }, "json");
        });
        $(".save-new").on("click", function() {
            const row = $(this).closest("tr");
            const data = {};
            row.find("input, select").each(function() {
                data[$(this).attr("name")] = $(this).val();
            });
            $.post("/add", data, function(resp) {
                if (!resp.success) alert("Error: " + resp.error);
                else location.reload();
            }, "json");
        });
        $("input[type=date]").datepicker({ dateFormat: "yy-mm-dd" });
    });
    </script>
    <style>
    .edit-table { border-collapse: collapse; width: 100%; margin-bottom: 2em; }
    .edit-table th, .edit-table td { border: 1px solid #ccc; padding: 5px; }
    .edit-table input, .edit-table select { width: 100%; }
    .new-entry { background: #f0f0f0; }
    </style>
    """)

    html_parts.append('</div>')
    return '\n'.join(html_parts)
