# Automated_Expense_Tracker
 Mini Projext 2024

# Pre-requisites:
	1. Python 3.11 or higher
    2. Python Modules - flask, numpy, opencv-python,
       pytesseract, PyPDF2, mysql-connector-python,
       pillow, python-dateutil, google-generativeai
	3. MySQL sever and command line
 	4. Windows OS

# Steps to setup and run the Automated_Expense_Tracker:

 1. Download all the files and extract them into a directory.

 2. Use the following commands to install the required modules
    pip install -r requirements.txt

3. Install MySQL server in the command line client.
   >https://dev.mysql.com/downloads/installer/ <--Download the installer from this link and install the server and command line client.<br>
   >--Select <b>full install</b> for installation type. <br> 
   >--Run MySql command line client after installation.<br>
   >--Refer sql_queries.txt for creating database.<br>
   >--Alternatively you can use MySQL workbench to create the database.
4. Install tesseract engine from    
https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe

5. Generate api key from<br>
https://ai.google.dev/gemini-api/docs/api-key<br>
and add api key in settings file
6. If using LLaMA download ollama,<br>
https://ollama.com/download
<br>install and configure model according to llama.md

8. Modify dbconnector.py with your database details (password and database_name).

9. Modify all the other fields to respective paths.

10. Open command propmt/Powershell in the downloaded directory and type "run.py" to start the server.

11. The Automated_Expense_Tracker is now live.



# Dashboard:

![image](https://github.com/user-attachments/assets/bb97def2-bd3d-4e36-b3c4-251f2224bcd8)

# Upload:

![image](https://github.com/user-attachments/assets/7f07b5bf-3372-4d34-8177-2e837d262679)

# Review:

![image](https://github.com/user-attachments/assets/7ea775d6-50e0-44fa-b94f-0e28b5d808f1)

# List of expenses:

![image](https://github.com/user-attachments/assets/54a620b1-5970-4094-be58-bb19b1a8c160)




