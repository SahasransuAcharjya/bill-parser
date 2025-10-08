# BillBot - Invoice Parser

A simple web application built with Flask and Tesseract OCR to automatically extract key details from uploaded invoice images.

## Features

- **Automatic Text Extraction:** Uses Tesseract OCR to read text from any invoice image.
- **Smart Data Parsing:** Employs regular expressions to find and extract important fields like Invoice Number, Dates, Seller/Buyer details, and Total Amount.
- **Interactive Web Interface:** A clean and modern UI with a drag-and-drop file uploader and a dark mode toggle.
- **Downloadable Results:** Users can download the extracted invoice details as a PDF summary.

## Tech Stack

- **Backend:** Python, Flask
- **OCR Engine:** Tesseract
- **Frontend:** HTML, CSS, JavaScript
- **Libraries:** OpenCV, Particles.js, jsPDF

## How to Run This Project Locally

### Prerequisites

- Python 3.x
- Tesseract OCR installed and configured in your system's PATH.
- A virtual environment (recommended).

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/SahasransuAcharjya/bill_parser.git](https://github.com/SahasransuAcharjya/bill_parser.git)
    cd bill_parser
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install the required Python packages:**
    ```bash
    pip install Flask Pillow pytesseract opencv-python
    ```

4.  **Run the Flask application:**
    ```bash
    python app.py
    ```

5.  Open your web browser and navigate to `http://127.0.0.1:5000`.

## How It Works

The application receives an uploaded image file and saves it to a temporary `uploads` folder. It then uses OpenCV to process the image and Tesseract to perform Optical Character Recognition (OCR), converting the image into a block of text. Finally, a set of regular expressions parse this text to find and display the invoice data on a results page.