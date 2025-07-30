import os
import json
import shutil
import mimetypes
import re
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env and configure Gemini
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-pro")

# Dynamic file hints by extension
FILE_HINTS = {
    ".pdf": "The following file is an invoice in PDF format.",
    ".png": "The following file is a scanned image of an invoice.",
    ".jpg": "The following file is a scanned image of an invoice.",
    ".jpeg": "The following file is a scanned image of an invoice.",
    ".xlsx": "The following file is an invoice spreadsheet (.xlsx format).",
    ".csv": "The following file is an invoice in CSV format."
}

# Shared prompt for all file types
BASE_PROMPT = """
The JSON structure shown below is the desired output format. 
Extract the information and return it in this exact JSON format. 
The extracted data should include client details, seller information, invoice metadata, itemized product details, and payment instructions.

Output only the JSON. Do not include explanations or formatting.

{
  "invoice": {
    "client_name": "",
    "client_address": "",
    "seller_name": "",
    "seller_address": "",
    "invoice_number": "",
    "invoice_date": "",
    "due_date": ""
  },
  "items": [
    {
      "description": "",
      "quantity": "",
      "total_price": ""
    }
  ],
  "subtotal": {
    "tax": "",
    "discount": "",
    "total": ""
  },
  "payment_instructions": {
    "due_date": "",
    "bank_name": "",
    "account_number": "",
    "payment_method": ""
  }
}
"""

def extract_json(text):
    """Extract clean JSON from Gemini output using regex."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            print("⚠️ Still failed to decode JSON after regex cleanup.")
            return None
    print("⚠️ No valid JSON block found in text.")
    return None

def convert_xlsx_to_csv(xlsx_path):
    """Convert an XLSX file to a CSV string."""
    try:
        df = pd.read_excel(xlsx_path, engine='openpyxl')
        csv_string = df.to_csv(index=False)
        return csv_string
    except Exception as e:
        print(f"❌ Error converting {xlsx_path} to CSV: {e}")
        return None

def extract_invoice(file_path):
    """Send file to Gemini and return structured JSON."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".xlsx":
        csv_data = convert_xlsx_to_csv(file_path)
        if not csv_data:
            return None
        file_data = csv_data.encode('utf-8')
        mime = "text/csv"
        ext = ".csv"
    else:
        with open(file_path, "rb") as f:
            file_data = f.read()
        mime, _ = mimetypes.guess_type(file_path)

    format_hint = FILE_HINTS.get(ext, "The following file is an invoice document.")
    final_prompt = format_hint + "\n\n" + BASE_PROMPT

    try:
        response = model.generate_content([
            final_prompt,
            {"mime_type": mime, "data": file_data}
        ])
        return extract_json(response.text)
    except Exception as e:
        print(f"❌ Gemini API Error for {file_path}: {e}")
        return None

def run_extractor():
    sorted_dir = "sorted_invoices"
    output_dir = "gemini_output"
    error_dir = "error_invoices"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(error_dir, exist_ok=True)

    for seller in os.listdir(sorted_dir):
        folder_path = os.path.join(sorted_dir, seller)
        if not os.path.isdir(folder_path):
            continue

        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            print(f"🔍 Extracting from: {file}")

            json_data = extract_invoice(file_path)
            json_name = os.path.splitext(file)[0] + ".json"
            output_path = os.path.join(output_dir, json_name)

            if json_data:
                with open(output_path, "w") as f:
                    json.dump(json_data, f, indent=2)
                print(f"✅ Saved JSON: {json_name}")
            else:
                print(f"❌ Extraction failed for {file}. Moved to error folder.")
                shutil.move(file_path, os.path.join(error_dir, file))

if __name__ == "__main__":
    run_extractor()
