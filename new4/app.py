from db_defs import *
from db_helpers import describe_possible_joins, add_all_and_commit, add_and_commit, delete_and_commit, execute_and_commit, generate_editable_table

if __name__ == "__main__":
    engine = create_engine("sqlite:///mydatabase.db", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        query = session.query(Person).outerjoin(Person.contacts)  # Beispiel: `contacts` ist Beziehung zu PersonContact
        rows = query.all()

        columns = [
            ("Person", "first_name", "First Name", False),
            ("Person", "last_name", "Last Name", False),
            ("Person", "comment", "Comment", False),
            ("contacts", "email", "Emails", True),
            ("contacts", "fax", "Faxes", True),
        ]


        html_table = generate_editable_table(rows, columns, id_column='id')

        print(html_table)
