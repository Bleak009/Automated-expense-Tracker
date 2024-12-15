from app import create_app
from dbconnector import create_database

create_database()
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
