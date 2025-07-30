import os
import shutil
import mimetypes
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-pro")

def convert_xlsx_to_csv(xlsx_path):
    """Convert an XLSX file to a CSV string."""
    try:
        df = pd.read_excel(xlsx_path, engine='openpyxl')
        csv_string = df.to_csv(index=False)
        return csv_string
    except Exception as e:
        print(f"❌ Error converting {xlsx_path} to CSV: {e}")
        return None

def extract_seller_name(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".xlsx":
        csv_data = convert_xlsx_to_csv(file_path)
        if not csv_data:
            return "Unknown"
        content = csv_data.encode('utf-8')
        mime = "text/csv"
    else:
        mime, _ = mimetypes.guess_type(file_path)
        with open(file_path, "rb") as f:
            content = f.read()

    prompt = "Extract only the **seller_name** from this invoice."
    response = model.generate_content([
        prompt,
        {"mime_type": mime, "data": content}
    ])
    return response.text.strip() or "Unknown"

def route_files():
    for file in os.listdir("input_invoices"):
        path = os.path.join("input_invoices", file)
        try:
            seller = extract_seller_name(path)
            target = os.path.join("sorted_invoices", seller)
            os.makedirs(target, exist_ok=True)
            shutil.move(path, os.path.join(target, file))
            print(f"✅ Moved {file} to {target}")
        except Exception as e:
            print(f"❌ Error with {file}: {e}")
            shutil.move(path, os.path.join("error_invoices", file))

if __name__ == "__main__":
    route_files()