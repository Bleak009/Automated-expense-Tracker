import mysql.connector
from mysql.connector import Error, pooling
import settings as sett

db_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=7,
    pool_reset_session=True,
    host=sett.DB_HOST,
    user=sett.DB_USER,
    password=sett.DB_PASSWORD,
    database=sett.DB_NAME
)

def connect_database():
    print("SQL connected")
    return db_pool.get_connection()

def disconnect_database(connection):
    if connection.is_connected():
        print("SQL disconnected")
        connection.close()

def create_database():
    expenses = """CREATE TABLE IF NOT EXISTS expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    expense_date DATE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
    );
    """

    categories = """CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
    );
    """

    connection = connect_database()
    cursor = connection.cursor()
    cursor.execute(expenses)
    cursor.execute(categories)
    disconnect_database(connection)
