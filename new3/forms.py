from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired

class AssignmentForm(FlaskForm):
    person_id = SelectField("Person", coerce=int, validators=[DataRequired()])
    abteilung_id = SelectField("Abteilung", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Speichern")
