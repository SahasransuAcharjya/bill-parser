import os
import re
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import cv2
import pytesseract

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def parse_invoice_details(text):
    def find(pattern, text, group=1, default=""):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(group).strip() if match else default

    invoice_data = {
        "Invoice Number": find(r"Invoice\s*(Number|No\.|ID|Details)[^\w\d]*([\w\d\-\/]+)", text, 2),
        "Order Number": find(r"Order\s*(Number|No\.|ID)[^\w\d]*([\w\d\-\/]+)", text, 2),
        "Invoice Date": find(r"Invoice\s*Date[^\d]*(\d{2}[\-\.]\d{2}[\-\.]\d{4}|\d{2}\/\d{2}\/\d{4})", text),
        "Order Date": find(r"Order\s*Date[^\d]*(\d{2}[\-\.]\d{2}[\-\.]\d{4}|\d{2}\/\d{2}\/\d{4})", text),
        "Seller Name": find(r"(Sold By|Seller)[^\n:]*:\s*([\w\s,&\-\.]+)", text, 2),
        "GSTIN": find(r"GST(IN|IN No\.| Registration No)[^\w]*([\w\d]+)", text, 2),
        "PAN": find(r"PAN\s*(No\.|Number)?[^\w]*([\w\d]+)", text, 2),
        "Seller Address": find(r"Seller (Registered Address|Address)[^\n]*:\s*([^\n]+)", text, 2),
        "Seller Phone": find(r"(Telephone|Phone)[^\d]*(\+?\d{8,})", text, 2),
        "Seller Email": find(r"(Email|E-mail)[^\w]*([\w\d.\-]+@[\w\d.\-]+)", text, 2),
        "Buyer Name": find(r"Billing Address[^\n:]*[:]*\s*([\w\s,&\-\.]+)", text, 1),
        "Billing Address": find(r"Billing Address[^\n:]*:\s*([^\n]+)", text, 1),
        "Buyer Phone": find(r"Phone[^\d]*(\+?\d{8,})", text),
        "Shipping Address": find(r"Shipping Address[^\n:]*:\s*([^\n]+)", text, 1),
        "Place of Supply": find(r"Place of supply[^\n:]*:\s*([^\n]+)", text, 1),
        "Place of Delivery": find(r"Place of delivery[^\n:]*:\s*([^\n]+)", text, 1),
        "Product Description": find(r"\d+\s+([^\n]+)\s+\d+\s+[^\n]+", text, 1),
        "Quantity": find(r"Qty\s*[:\-]?\s*(\d+)", text),
        "Unit Price": find(r"(Unit Price|Gross Amount)\s*[:\-]?\s*(₹?\d+\.?\d*)", text, 2),
        "Discount": find(r"Discount\s*[:\-]?\s*(₹?\d+\.?\d*)", text),
        "Taxable Value": find(r"Taxable Value\s*[:\-]?\s*(₹?\d+\.?\d*)", text),
        "Tax Rate": find(r"Tax Rate\s*[:\-]?\s*([\d\.]+%?)", text),
        "Tax Type": find(r"Tax Type\s*[:\-]?\s*(\w+)", text),
        "Tax Amount": find(r"Tax Amount\s*[:\-]?\s*(₹?\d+\.?\d*)", text),
        "Total Item Amount": find(r"Total Amount\s*[:\-]?\s*(₹?\d+\.?\d*)", text),
        "Total Quantity": find(r"TOTAL QTY\s*[:\-]?\s*(\d+)", text),
        "Total Amount": find(r"TOTAL PRICE\s*[:\-]?\s*(₹?\d+\.?\d*)", text),
        "Grand Total": find(r"(Grand Total|TOTAL)\s*[:\-₹]?\s*(₹?\d+\.?\d*)", text, 2),
        "Amount in Words": find(r"Amount in Words[^\n:]*:\s*([^\n]+)", text),
        "Mode of Payment": find(r"Mode of Payment[^\n:]*:\s*([^\n]+)", text),
        "Payment Transaction ID": find(r"Payment Transaction ID[^\n]*:\s*([^\n]+)", text, 1),
        "Invoice Value": find(r"Invoice Value[^\n:]*[:\-]?\s*(₹?\d+\.?\d*)", text)
    }
    return invoice_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_invoice():
    if 'invoice' not in request.files:
        return render_template('results.html', result={"Error": "No file part"})
    file = request.files['invoice']
    if file.filename == '':
        return render_template('results.html', result={"Error": "No selected file"})
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Read image and perform OCR
    image = cv2.imread(file_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)

    # Parse extracted fields
    parsed_data = parse_invoice_details(text)
    return render_template('results.html', result=parsed_data)

if __name__ == '__main__':
    app.run(debug=True)
