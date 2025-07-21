# app.py
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from db_ops import get_joined_data, update_row, delete_row, insert_row

app = Flask(__name__)
DATABASE = "test.db"

from join_views import join_views  # ausgelagert, falls gewünscht

def get_conn():
    return sqlite3.connect(DATABASE)

@app.route("/")
def index():
    return "<h1>Available views</h1>" + "<br>".join(
        f'<a href="/view/{name}">{name}</a>' for name in join_views
    )

@app.route("/view/<view>")
def view_data(view):
    conn = get_conn()
    data = get_joined_data(conn, join_views[view])
    return render_template("view.html", rows=data, view=view, columns=join_views[view]["columns"])

@app.route("/edit/<view>/<int:row_id>", methods=["POST"])
def edit(view, row_id):
    conn = get_conn()
    data = request.form.to_dict()
    data["id"] = row_id
    update_row(conn, join_views[view], data)
    return redirect(url_for("view_data", view=view))

@app.route("/delete/<view>/<int:row_id>")
def delete(view, row_id):
    conn = get_conn()
    delete_row(conn, join_views[view], row_id)
    return redirect(url_for("view_data", view=view))

@app.route("/add/<view>", methods=["POST"])
def add(view):
    conn = get_conn()
    data = request.form.to_dict()
    insert_row(conn, join_views[view], data)
    return redirect(url_for("view_data", view=view))

if __name__ == "__main__":
    app.run(debug=True)

