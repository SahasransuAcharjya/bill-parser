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

def multi_find(patterns, text, group=1, default=""):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match and match.group(group) is not None:
            return match.group(group).strip()
    return default

def capture_after(label, text, max_lines=3):
    lines = text.splitlines()
    idx = [i for i, l in enumerate(lines) if label.lower() in l.lower()]
    if idx:
        result = []
        for offset in range(1, max_lines+1):
            if idx[0]+offset < len(lines):
                line = lines[idx[0]+offset].strip()
                if line:
                    result.append(line)
        return " ".join(result)
    return ""

def extract_fields(text):
    invoice_patterns = [
        r"Invoice\s*(Number|No\.|ID|Details)[^\w\d]*([\w\d\-\/]+)",
        r"Invoice No[_:]?[\s]*([\w\d\-\/]+)"
    ]
    order_patterns = [
        r"Order\s*(Number|No\.|ID)[^\w\d]*([\w\d\-\/]+)",
        r"Order ID[_:]?[\s]*([\w\d\-\/]+)"
    ]
    invoice_date_patterns = [
        r"Invoice\s*Date[_:]?[^\d]*(\d{2}[\-\.]\d{2}[\-\.]\d{4})",
        r"Invoice Date[_:]?\s*(\d{2}\/\d{2}\/\d{4})"
    ]
    order_date_patterns = [
        r"Order\s*Date[_:]?[^\d]*(\d{2}[\-\.]\d{2}[\-\.]\d{4})",
        r"Order Date[_:]?\s*(\d{2}\/\d{2}\/\d{4})"
    ]
    seller_patterns = [
        r"Sold By\s*[:\-]?\s*([^\n,]+)",
        r"Seller Registered Address[:\-]?\s*([^\n,]+)"
    ]
    gstin_patterns = [
        r"GST(IN|IN No\.| Registration No)[^\w]*([A-Z0-9]+)",
        r"GSTIN[:\-]?\s*([A-Z0-9]+)"
    ]
    pan_patterns = [
        r"PAN\s*(No\.|Number)?[^\w]*([A-Z0-9]+)"
    ]
    seller_addr_patterns = [
        r"Sold By\s*[:\-]?\s*(.+?)(?=GSTIN|PAN|$)",
        r"Seller Registered Address\s*[:\-]?\s*(.+?)(?=GSTIN|PAN|$)"
    ]
    buyer_name = multi_find([r"Billing Address\s*[:\-]?\s*([\w \-,\.]+)"], text) or capture_after("Billing Address", text, max_lines=1)
    billing_addr = capture_after("Billing Address", text, max_lines=2)
    shipping_addr = multi_find([r"Shipping Address\s*[:\-]?\s*([\w \-,\.]+)"], text) or capture_after("Shipping Address", text, max_lines=2)
    place_supply = multi_find([r"Place of supply\s*[:\-]?\s*([\w \-,\.]+)"], text)
    place_delivery = multi_find([r"Place of delivery\s*[:\-]?\s*([\w \-,\.]+)"], text)

    product_pattern = r"\n([\w ,\-()\[\]/]+)\s+HSN:.*IGST:.*?\s+(\d+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"
    m_prod = re.search(product_pattern, text)
    if m_prod:
        desc = m_prod.group(1)
        qty = m_prod.group(2)
        gross_price = m_prod.group(3)
        discount = m_prod.group(4)
        taxable_val = m_prod.group(5)
        igst = m_prod.group(6)
        total = m_prod.group(7)
    else:
        desc = multi_find([r"Description\s*\n([^\n]+)"], text)
        qty = multi_find([r"\bQty[\s:]*([0-9]+)"], text)
        gross_price = multi_find([r"Gross\s*Amount[\s:]*([\d.\-]+)"], text)
        discount = multi_find([r"Discount[\s:]*([\d.\-]+)"], text)
        taxable_val = multi_find([r"Taxable Value[\s:]*([\d.\-]+)"], text)
        igst = multi_find([r"IGST[\s:]*([\d.\-]+)"], text)
        total = multi_find([r"TOTAL PRICE[\s:]*([\d.\-]+)"], text)
    
    total_qty = multi_find([r"TOTAL QTY[\s:]*([0-9]+)"], text)
    total_amount = multi_find([r"TOTAL PRICE[\s:]*([\d.\-]+)"], text)
    grand_total = multi_find([r"Grand Total[\s:₹]*([\d.\-]+)"], text)
    amount_words = multi_find([r"Amount in Words[\s:]*([^\n]+)"], text)
    mode_payment = multi_find([r"Mode of Payment[\s:]*([^\n]+)"], text)
    payment_tx_id = multi_find([r"Payment Transaction ID[\s:]*([^\n]+)"], text)
    invoice_value = multi_find([r"Invoice Value[\s:]*([\d.\-]+)"], text)

    extracted = {
        "Invoice Number": multi_find(invoice_patterns, text),
        "Order Number": multi_find(order_patterns, text),
        "Invoice Date": multi_find(invoice_date_patterns, text),
        "Order Date": multi_find(order_date_patterns, text),
        "Seller Name": multi_find(seller_patterns, text),
        "GSTIN": multi_find(gstin_patterns, text),
        "PAN": multi_find(pan_patterns, text),
        "Seller Address": multi_find(seller_addr_patterns, text),
        "Buyer Name": buyer_name,
        "Billing Address": billing_addr,
        "Shipping Address": shipping_addr,
        "Place Of Supply": place_supply,
        "Place Of Delivery": place_delivery,
        "Product Description": desc,
        "Quantity": qty,
        "Unit Price": gross_price,
        "Discount": discount,
        "Taxable Value": taxable_val,
        "Tax Rate": "12%",   # Set from context or table if needed
        "Tax Type": "IGST",  # Set from context or table if needed
        "Tax Amount": igst,
        "Total Item Amount": total,
        "Total Quantity": total_qty,
        "Total Amount": total_amount,
        "Grand Total": grand_total,
        "Amount In Words": amount_words,
        "Mode Of Payment": mode_payment,
        "Payment Transaction Id": payment_tx_id,
        "Invoice Value": invoice_value,
    }
    return extracted

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
