import os
import re
import cv2
import json
import logging
import numpy as np
import pytesseract
import PyPDF2
import google.generativeai as genai
from mysql.connector import Error
from datetime import datetime
from dateutil.parser import parse
from dbconnector import connect_database, disconnect_database
import settings as sett



######################################## DASHBOARD ################################################

def fetch_donut_chart_data():
    connection = None
    try:
        # Connect to the database
        connection = connect_database()
        cursor = connection.cursor()

        # Query to fetch category-wise expense data
        query = """
        SELECT c.category_name, SUM(e.amount) AS total_amount
        FROM expenses e
        JOIN categories c ON e.category_id = c.category_id
        GROUP BY c.category_name
        ORDER BY total_amount DESC;
        """
        cursor.execute(query)
        result = cursor.fetchall()
        # Convert the result to a dictionary
        category_data = {row[0]: row[1] for row in result}
        return category_data

    except Error as e:
        print(f"Error (donut): '{e}'")
        return None

    finally:
        # Disconnect the database
        if connection:
            disconnect_database(connection)

def fetch_expense_data_for_line_chart(months):
    connection = None
    try:
        # Database connection
        connection = connect_database()
        cursor = connection.cursor()

        # Query to fetch expense data for the last 'months' months
        query = """
        SELECT expense_date, SUM(amount) as total_amount
        FROM expenses
        WHERE expense_date >= DATE(NOW()) - INTERVAL %s MONTH
        GROUP BY expense_date
        ORDER BY expense_date;
        """
        cursor.execute(query, (months,))
        result = cursor.fetchall()

        # Prepare data for line chart
        dates = []
        amounts = []

        for row in result:
            date = row[0].strftime('%Y-%m-%d')  # Format date as 'YYYY-MM-DD'
            amount = row[1]
            dates.append(date)
            amounts.append(amount)

        return {"dates": dates, "amounts": amounts}

    except Error as e:
        print(f"Error (line): '{e}'")
        return None

    finally:
        # Close the database connection
        if connection:
            disconnect_database(connection)


def fetch_expenses_by_timeframe():
    connection = None
    try:
        # Connect to the database
        connection = connect_database()
        cursor = connection.cursor()  # Custom function to connect to the database

        # Get current day, month, and year
        today = datetime.now().date()
        current_month = today.month
        current_year = today.year

        # Query for today's expenses
        query_day = """
        SELECT SUM(amount) as total_amount
        FROM expenses
        WHERE expense_date = %s;
        """
        cursor.execute(query_day, (today,))
        day_expenses = cursor.fetchone()[0] or 0  # Default to 0 if no data

        # Query for current month's expenses
        query_month = """
        SELECT SUM(amount) as total_amount
        FROM expenses
        WHERE MONTH(expense_date) = %s AND YEAR(expense_date) = %s;
        """
        cursor.execute(query_month, (current_month, current_year))
        month_expenses = cursor.fetchone()[0] or 0
        
        # Query for current year's expenses
        query_year = """
        SELECT SUM(amount) as total_amount
        FROM expenses
        WHERE YEAR(expense_date) = %s;
        """

        cursor.execute(query_year, (current_year,))
        year_expenses = cursor.fetchone()[0] or 0


        # Return the results as a dictionary
        return {
            "day_expenses": float(day_expenses),
            "month_expenses": float(month_expenses),
            "year_expenses": float(year_expenses),
        }

    except Error as e:
        print(f"Error: '{e}'")
        return None

    finally:
        # Disconnect from the database
        if connection:
            disconnect_database(connection)  # Custom function to close the connection

######################################## UPLOAD ################################################

# Function to preprocess image
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    if height < 800 or width < 800:
        gray = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_LINEAR)
    denoised = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cwd = os.getcwd()
    output_path = os.path.join(cwd,'Project','app', 'static', 'processed_image.png')
    cv2.imwrite(output_path, binary)
    print(f"Processed image saved at: {output_path}")
    return binary

# Function to extract text using pytesseract
def extract_text(image):
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(image, config=custom_config)
    print("\n\nfirst: "+text)
    return text

# Function to clean and normalize extracted text
def clean_extracted_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    extracted_text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        extracted_text += page.extract_text()
    print("\n\n"+extracted_text)
    return extracted_text

def process_image(img_cv):
    try:
        preprocessed_image = preprocess_image(img_cv)  # Add your preprocessing logic here
        extracted_text = extract_text(preprocessed_image)
        print("\n\nraw: "+extracted_text)  # OCR extraction
        cleaned_text = clean_extracted_text(extracted_text)

        # Get response from categorization model
        llama_response = categorize_data(cleaned_text)
        print("\n\nLlama response: " + llama_response)

        # Extract JSON from response
        expense_data = extract_json(llama_response)
        return expense_data

    except Exception as e:
        logging.error("Error processing image: %s", e, exc_info=True)
        



######################################## LLAMA ################################################


# def categorize_data(text_query):

#     response = ollama.chat(
#     model="sett.llama_model",
#     messages=[{"role": "user", "content": text_query}],
#     )

#     return response.get("message", {}).get("content", "")


system_promtpt = """Analyze the provided transaction data and identify the first 5 expenses. For each expense, extract and categorize the information into the following JSON format:

[{
  "Title": "<Title of the transaction>",
  "Date": "<YYYY-MM-DD>",
  "Expense Amount": "<Amount>",
  "Category": "<Category>"
}]

Please ensure that:
1. The "Title" is the descriptive name of the transaction.
2. The "Date" follows the format YYYY-MM-DD.
3. The "Expense Amount" is the numerical amount associated with the transaction.
4. Json should always be an array, even if only one expense is identified.
5. The "Category" should be one of these:[Bills,Car,Clothing,Education,Electronics,Entertainment,Food,Health,Home,Insurance,Shopping,Social,Sport,Tax,Telephone,Transportation,unkown].
"""


def categorize_data(text_query):
    
    genai.configure(sett.api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_promtpt)
    response = model.generate_content(text_query)
    print(response.text)

    return response.text

def extract_json(response_text):
    import re
    import json
    
    # Extract the JSON block enclosed by triple backticks
    match = re.search(r"```(.*?)```", response_text, re.DOTALL)
    if match:
        json_text = match.group(1).strip()
        
        # Remove the word "json" if it appears at the start of the block
        if json_text.lower().startswith("json"):
            json_text = json_text[4:].strip()  # Remove "json" and the following space/newline
        
        # Remove commas from numeric values
        json_text = re.sub(r'(\d+),(\d+)', r'\1\2', json_text)
        json_text = re.sub(r'[$€£₹]', '', json_text) 
        
        try:
            # Parse the JSON
            parsed_data = json.loads(json_text)
            print("\n\n", parsed_data)
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    else:
        print("No JSON block found in the response.")
        return None

def convert_dates(data):
    from datetime import datetime

def convert_to_yyyymmdd(date_str):
    # List of possible date formats to parse
    possible_formats = [
        '%Y-%m-%d',  # Already in the correct format
        '%d-%m-%Y',
        '%d-%y-%m',
        '%m-%d-%Y',
        '%m-%y-%d',
        '%d-%m-%y',
        '%m-%d-%y',
        '%y-%m-%d'  # Already in reverse format
    ]
    
    for fmt in possible_formats:
        try:
            # Try to parse the date with the current format
            parsed_date = datetime.strptime(date_str, fmt)
            # Convert and return in 'YYYY-MM-DD' format
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue  # Try the next format if parsing fails
    try:
        parsed_date = parse(date_str, fuzzy=True)
        return parsed_date.strftime('%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format: {date_str}")
        return None

    # If no format matches, return None
    print(f"Invalid date format: {date_str}")
    return None


def get_category_id(category_name, cursor):
    query = "SELECT category_id FROM categories WHERE category_name = %s"
    cursor.execute(query, (category_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return 17  # Default to 'unknown'


def insert_expenses(json_data):
    connection = connect_database()
    cursor = connection.cursor()

    for expense in json_data:
        try:
            # Convert category name to category_id
            category_id = get_category_id(expense['Category'], cursor)

            # Check for duplicate entry
            duplicate_query = """
                SELECT expense_id 
                FROM expenses 
                WHERE expense_date = %s AND amount = %s
            """
            duplicate_values = (
                convert_to_yyyymmdd(expense['Date']),
                expense['Expense Amount'],
            )
            cursor.execute(duplicate_query, duplicate_values)
            duplicate = cursor.fetchone()

            if duplicate:
                print(f"\nDuplicate detected for expense: {expense}. Skipping insert.")
                continue

            # Prepare and execute the SQL query
            insert_query = """
                INSERT INTO expenses (expense_date, amount, description, category_id)
                VALUES (%s, %s, %s, %s)
            """
            insert_values = (
                convert_to_yyyymmdd(expense['Date']),
                expense['Expense Amount'],
                expense['Title'],
                category_id
            )
            cursor.execute(insert_query, insert_values)
            print(f"\nExpense inserted: {expense}.")

        except Exception as e:
            print(f"Error inserting expense: {expense}, Error: {e}")

    # Commit the transaction and close the connection
    connection.commit()
    if connection:
        disconnect_database(connection)  # Custom function to close the connection



########################################### MANUAL ########################################
def check_duplicate_transaction(expense_date, amount, description, category_id):
    """
    Check if a transaction with the same details already exists in the database.
    """
    connection = None
    try:
        connection = connect_database()
        cursor = connection.cursor()
        query = """
            SELECT COUNT(*) FROM expenses 
            WHERE expense_date = %s AND amount = %s AND description = %s AND category_id = %s
        """
        cursor.execute(query, (expense_date, amount, description, category_id))
        duplicate_count = cursor.fetchone()[0]
        return duplicate_count > 0
    except Error as e:
        print(f"Error (check duplicate): {e}")
        return False
    finally:
        if connection:
            disconnect_database(connection)

def add_new_transaction(expense_date, amount, description, category_id):
    """
    Add a new transaction to the database.
    """
    connection = None
    try:
        connection = connect_database()
        cursor = connection.cursor()
        query = """
            INSERT INTO expenses (expense_date, amount, description, category_id)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (expense_date, amount, description, category_id))
        connection.commit()
        return True
    except Error as e:
        print(f"Error (add transaction): {e}")
        return False
    finally:
        if connection:
            disconnect_database(connection)


################################ LIST ######################################

def fetch_all_expenses():
    """
    Fetch all expenses from the database, including category names.
    Returns:
        A list of expense dictionaries or None if an error occurs.
    """
    connection = None
    try:
        # Connect to the database
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        # Query to fetch expenses and their categories
        query = """
            SELECT e.expense_id, e.expense_date, e.amount, e.description, 
                   COALESCE(c.category_name, 'Unknown') AS category
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.category_id
            ORDER BY e.expense_date DESC
        """
        cursor.execute(query)
        expenses = cursor.fetchall()
        return expenses

    except Exception as e:
        print(f"Error fetching expenses: {e}")
        return None
    finally:
        # Close the database connection
        if connection:
            disconnect_database(connection)


def fetch_expense_by_id(expense_id):
    """
    Fetch a single expense by its ID.
    """
    connection = None
    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM expenses WHERE expense_id = %s"
        cursor.execute(query, (expense_id,))
        expense = cursor.fetchone()
        return expense
    except Exception as e:
        print(f"Error fetching expense by ID: {e}")
        return None
    finally:
        if connection:
            disconnect_database(connection)

def update_expense(expense_id, expense_date, amount, description, category_id):
    """
    Update an expense in the database.
    """
    connection = None
    try:
        connection = connect_database()
        cursor = connection.cursor()
        query = """
            UPDATE expenses 
            SET expense_date = %s, amount = %s, description = %s, category_id = %s 
            WHERE expense_id = %s
        """
        cursor.execute(query, (expense_date, amount, description, category_id, expense_id))
        connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating expense: {e}")
        return False
    finally:
        if connection:
            disconnect_database(connection)

def delete_expense(expense_id):
    """
    Delete an expense from the database.
    """
    connection = None
    try:
        connection = connect_database()
        cursor = connection.cursor()
        query = "DELETE FROM expenses WHERE expense_id = %s"
        cursor.execute(query, (expense_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting expense: {e}")
        return False
    finally:
        if connection:
            disconnect_database(connection)


################ TEST ###################

def fetch_expenses_as_json():
    connection = None
    try:
        # Establish connection to the MySQL database
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        # SQL query to fetch all data from the 'expenses' table
        query = "SELECT * FROM expenses;"
        cursor.execute(query)

        # Fetch all rows from the query result
        rows = cursor.fetchall()

        # Convert the fetched rows to JSON format
        json_data = json.dumps(rows, indent=4, default=str)  # Convert to JSON, use default=str for date handling

        return json_data

    except Exception as e:
        print(f"Error deleting expense: {e}")
        return False
    finally:
        if connection:
            disconnect_database(connection)

insight_prompt = """Generate insights in 100 words, points.
[
  { "id": 1, "category": "Bills", "description": "Utility and other bills" },
  { "id": 2, "category": "Car", "description": "Expenses related to car maintenance and fuel" },
  { "id": 3, "category": "Clothing", "description": "Clothes and accessories" },
  { "id": 4, "category": "Education", "description": "Tuition fees and educational materials" },
  { "id": 5, "category": "Electronics", "description": "Gadgets and electronic devices" },
  { "id": 6, "category": "Entertainment", "description": "Movies, events, and other entertainment" },
  { "id": 7, "category": "Food", "description": "Meals and groceries" },
  { "id": 8, "category": "Health", "description": "Healthcare and medical expenses" },
  { "id": 9, "category": "Home", "description": "Rent, furniture, and household items" },
  { "id": 10, "category": "Insurance", "description": "Insurance premiums" },
  { "id": 11, "category": "Shopping", "description": "General shopping expenses" },
  { "id": 12, "category": "Social", "description": "Social activities and events" },
  { "id": 13, "category": "Sport", "description": "Sports equipment and memberships" },
  { "id": 14, "category": "Tax", "description": "Tax payments" },
  { "id": 15, "category": "Telephone", "description": "Phone bills and internet charges" },
  { "id": 16, "category": "Transportation", "description": "Public transport and travel costs" },
  { "id": 17, "category": "Unknown", "description": "Uncategorizable data" }
]
"""
def generate_insight(text_query):
    
    genai.configure(api_key="AIzaSyCo6lx7LXDA1c_A4dmegvf9qczM5r9E_0c")
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=insight_prompt)
    response = model.generate_content(text_query)
    print(response.text)

    return response.text
