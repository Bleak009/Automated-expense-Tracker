from flask import Flask, jsonify, render_template, Blueprint , request , session, redirect, url_for, flash
from app.models import *
import logging
import json
import io
import base64
from PIL import Image



from flask import current_app as app

main = Blueprint('main', __name__)

@main.route("/")
def dashboard():
    return render_template("dashboard.html")

# Example route for fetching donut chart data
@main.route('/api/expenses/donut-chart', methods=['GET'])
def get_donut_chart_data():
    # Example data fetched from a database or a computation
    category_data = fetch_donut_chart_data()
    
    # Return data as JSON
    if category_data:
        return jsonify(category_data)
    else:
        return jsonify({"error": "Failed to fetch line chart data"}), 500

# API endpoint to fetch data for line chart
@main.route("/api/line-chart-data", methods=['GET'])
def line_chart_data():
    months = request.args.get('months', type=int, default=1)  
    data = fetch_expense_data_for_line_chart(months)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch line chart data"}), 500

@main.route("/api/summary-data", methods=['GET'])
def summary_data():
    data = fetch_expenses_by_timeframe()
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch summary data"}), 500



######################################## UPLOAD ################################################

pytesseract.pytesseract.tesseract_cmd = sett.tesseract_path

@main.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        if 'file' in request.files:  # Handle file uploads
            f = request.files['file']
            if f:
                try:
                    img = Image.open(f.stream)
                    img_cv = np.array(img)
                    expense_data =  process_image(img_cv)
                    session['expense_data'] = expense_data
                    return redirect(url_for('main.review'))
                except Exception as e:
                    logging.error("Error processing image: %s", e, exc_info=True)
                    return render_template('error.html', message="Failed to process the image.")
        elif request.is_json:  # Handle base64-encoded image data
            try:
                data = request.get_json()
                if 'image' not in data:
                    return {"error": "No image data provided"}, 400

                # Decode base64 image
                image_data = data['image'].split(",")[1]
                image_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(image_bytes))
                img_cv = np.array(img)
                expense_data = process_image(img_cv)
                session['expense_data'] = expense_data
                return {"redirect_url": url_for('main.review')}, 200
            except Exception as e:
                logging.error("Error processing image: %s", e, exc_info=True)
                return render_template('error.html', message="Failed to process the image.")
    return render_template('upload.html')



# Route to upload PDF
@main.route('/upload-pdf', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        # Check if the user has uploaded a file
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        # If a file was uploaded, process it
        if file.filename != '':
            # Extract text from the uploaded PDF file
            extracted_text = extract_text_from_pdf(file)
            # Get response from categorization model
            llama_response = categorize_data(extracted_text)
                
            # Extract JSON from response
            expense_data = extract_json(llama_response)
                
            # Convert dates to the desired format
            #convert_dates(expense_data)

                
            session['expense_data'] = expense_data
                
            return redirect(url_for('main.review'))
    return render_template('upload.html')



@main.route('/add-transaction', methods=['POST'])
def add_transaction():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('person-place')
        category_id = request.form.get('category_id')
        expense_date = request.form.get('transaction-date')
        amount = request.form.get('total-amount')

        # Validate required fields
        if not all([name, category_id, expense_date, amount]):
            flash("All fields are required.", "error")
            return redirect(url_for('main.dashboard'))

        # Check for duplicates
        is_duplicate = check_duplicate_transaction(expense_date, amount, name, category_id)
        if is_duplicate:
            flash("Duplicate transaction found. No data was added.", "warning")
        else:
            # Add the transaction if no duplicate exists
            success = add_new_transaction(expense_date, amount, name, category_id)
            if success:
                flash("Transaction added successfully!", "success")
            else:
                flash("An error occurred while adding the transaction.", "error")

        return redirect(url_for('main.dashboard'))


@main.route('/review', methods=['GET', 'POST'])
def review():
    if request.method == 'POST':
        # Fetch all form data
        reviewed_data = request.form.to_dict(flat=False)
        print("\n\nRaw reviewed data:", reviewed_data)

        # Extract and format nested data
        formatted_data = []
        for key, value in reviewed_data.items():
            if key.startswith("data["):
                # Extract the index and field name
                field_match = re.match(r'data\[(\d+)\]\[(.+)\]', key)
                if field_match:
                    index, field_name = field_match.groups()
                    index = int(index) - 1  # Adjusting for zero-based index

                    # Ensure the corresponding expense dict exists
                    while len(formatted_data) <= index:
                        formatted_data.append({})

                    # Assign the value to the correct field
                    formatted_data[index][field_name] = value[0]

        print("\n\nFormatted reviewed data:", formatted_data)

        # Example: Insert into database
        if formatted_data:
            insert_expenses(formatted_data)
        return redirect(url_for('main.dashboard'))
    
    # Render the review page with the session data
    expense_data = session.get('expense_data', [])
    if not expense_data:
        logging.warning("No expense data found in session.")
        return render_template('error.html', message="OCR couldnt scan the data. Please try again.")

    return render_template('review.html', expense_data=expense_data)



@main.route('/transactions', methods=['GET'])
def list():
    """
    Route to display all expenses in a list view.
    """
    # Fetch expenses using the model function
    expenses = fetch_all_expenses()
    
    if expenses is None:
        # If fetching expenses fails, render an error page
        flash("Error fetching expensas")

    # Pass the data to the template
    return render_template('list.html', expenses=expenses)

@main.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):

    if request.method == 'POST':
        # Get data from the form
        expense_date = request.form.get('expense_date')
        amount = request.form.get('amount')
        description = request.form.get('description')
        category_id = request.form.get('category_id')

        # Update the expense in the database
        success = update_expense(expense_id, expense_date, amount, description, category_id)
        if success:
            flash("Expense updated successfully!", "success")
        else:
            flash("Failed to update the expense.", "error")
        return redirect(url_for('main.list'))

    # Fetch expense details for the form
    expense = fetch_expense_by_id(expense_id)
    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for('main.list'))

    return render_template('edit_expense.html', expense=expense)


@main.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense_route(expense_id):

    success = delete_expense(expense_id)
    if success:
        flash("Expense deleted successfully!", "success")
    else:
        flash("Failed to delete the expense.", "error")
    return redirect(url_for('main.list'))


##########################################

@main.route('/insights', methods=['GET'])
def insights():
    json_data = fetch_expenses_as_json()

    if not json_data:
        return "Error fetching data from the database."

    try:
        insights_text = generate_insight(json_data)
    except Exception as e:
        return f"Error generating insights: {e}"

    return render_template('insights.html', insights=insights_text)