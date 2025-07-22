from flask import Flask, request, jsonify
from db_defs import Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import create_engine
from db_helper import generate_admin_html

app = Flask(__name__)
engine = create_engine("sqlite:///your.db")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

@app.route("/")
def admin_ui():
    session = Session()
    return generate_admin_html(Base, session, header_labels={
        "abteilung.abteilungsleiter_id": "Abteilungsleiter"
    })

@app.route("/update", methods=["POST"])
def update_cell():
    try:
        name = request.form["name"]
        value = request.form["value"]
        _, rowid, column = name.split("_", 2)
        # handle update logic
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route("/add", methods=["POST"])
def add_row():
    try:
        # parse form data and insert new row
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True)
