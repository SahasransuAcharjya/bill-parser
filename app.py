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

def safe_field(patterns, text, idx=1):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(idx).strip()
    return ""

def extract_recipient_and_address(text):
    # Look for buyer in Shipping Address, Billing Address, or floating above the address block.
    lines = text.split('\n')
    address = ""
    buyer = ""
    # Priority logic: try each known block label, fallback to any properly formatted address block
    candidate_labels = ["shipping address", "billing address", "ship to", "bill to"]
    for label in candidate_labels:
        for i, line in enumerate(lines):
            if label in line.lower():
                # Harvest all lines below until blank or next ALLCAPS
                block = []
                for l2 in lines[i+1:]:
                    if not l2.strip() or re.match(r"^[A-Z][A-Z0-9 /().,-]*:?$", l2):
                        break
                    block.append(l2.strip())
                if block:
                    buyer = block[0] if block else ""
                    address = ', '.join(block[1:]) if len(block) > 1 else ""
                    if buyer: return buyer, address
    # Fallback: scan for common address pattern just after any recognizable name
    for i, line in enumerate(lines):
        if re.match(r"[A-Za-z][A-Za-z .'-]+$", line) and i + 1 < len(lines):
            block = []
            for l2 in lines[i+1:]:
                if not l2.strip() or re.match(r"^[A-Z][A-Z0-9 /().,-]*:?$", l2):
                    break
                block.append(l2.strip())
            if block:
                buyer = line.strip()
                address = ', '.join(block)
                return buyer, address
    return "", ""

def extract_fields(text):
    invoice_no   = safe_field([r"Invoice (No|Number)[\s:]*([\w\-]+)"], text, 2)
    order_no     = safe_field([r"Order (Id|Number)[\s:]*([\w\-]+)"], text, 2)
    invoice_date = safe_field([r"Invoice Date[\s:]*([0-9]{2}[./-][0-9]{2}[./-][0-9]{4})"], text)
    seller       = safe_field([r"Sold By[\s:]*([^\n,]+)"], text)
    gstin        = safe_field([r"GST(IN| Registration No)[\s:]*([A-Z0-9]+)"], text, 2)
    buyer_name, buyer_address = extract_recipient_and_address(text)
    prod_desc = safe_field([r"Description[^\n]*\n([^\n]+)"], text)
    qty = safe_field([r"Qty[\s:]*([0-9]+)"], text)
    total_amt = safe_field([r"(TOTAL (AMOUNT|PRICE)[^\d]*([\d\.]+))"], text, 3)

    return {
        "Invoice Number": invoice_no,
        "Order Number": order_no,
        "Invoice Date": invoice_date,
        "Seller Name": seller,
        "GSTIN": gstin,
        "Buyer Name": buyer_name,
        "Buyer Address": buyer_address,
        "Product Description": prod_desc,
        "Quantity": qty,
        "Total Amount": total_amt
    }

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
    image = cv2.imread(file_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    parsed_data = extract_fields(text)
    return render_template('results.html', result=parsed_data)

if __name__ == '__main__':
    app.run(debug=True)
