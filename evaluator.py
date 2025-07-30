import os
import json
import yaml
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. CONFIGURATION ---
# Load the configuration to know which fields Gemini should compare.
with open("config.yaml") as f:
    config = yaml.safe_load(f)
deal_breakers = set(config["deal_breakers"])

# Gemini API setup
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-pro")

# --- 2. PROMPT ENGINEERING: Instructing the "Gemini Referee" ---
def build_prompt(gt_data, output_data, deal_breakers_set, file_name):
    """
    Builds a prompt that commands Gemini to act as a referee, compare the two JSON inputs,
    and return its verdict as a new, structured JSON object.
    """
    deal_breakers_str = "\n".join(f"- {db}" for db in sorted(list(deal_breakers_set)))
    
    return f"""
You are a precise JSON-producing invoice evaluator. Your task is to perform a STRICT comparison between the GROUND TRUTH and the EXTRACTED OUTPUT for the invoice named `{file_name}`.

Your response MUST be a single, valid JSON object and nothing else. Do not include any text before or after the JSON.

Compare ONLY the following fields:
{deal_breakers_str}

GROUND TRUTH:
{json.dumps(gt_data, indent=2)}

EXTRACTED OUTPUT:
{json.dumps(output_data, indent=2)}

Comparison Rules:
1.  You must perform a strict, character-by-character comparison.
2.  The ONLY exceptions for a Match are: case-insensitivity and leading/trailing whitespace.
3.  Ignore all whitespaces when comparing the EXTRACTED OUTPUT and GROUND TRUTH.
4.  Any other difference is a Mismatch. This includes currency symbols, commas, or other formatting.

JSON Output Structure (Your Verdict):
- The JSON object must have a key "overall_status" which is either "Pass" or "Mismatch".
- If the status is "Mismatch", it must also include a key "mismatches", which is a list of objects.
- Each object in the "mismatches" list must have three keys: "field", "expected", and "actual".
- If the status is "Pass", the "mismatches" list must be empty.

Example of a Mismatch Verdict:
{{
  "overall_status": "Mismatch",
  "mismatches": [
    {{
      "field": "total",
      "expected": "$100.00",
      "actual": "100.00"
    }}
  ]
}}

Example of a Pass Verdict:
{{
  "overall_status": "Pass",
  "mismatches": []
}}

Now, provide your verdict as a JSON response for the given invoice data.
"""

# --- 3. ORCHESTRATION: Managing the Comparison ---
results = []

for file in sorted(os.listdir("ground_truth")):
    if not file.endswith(".json"):
        continue

    base = os.path.splitext(file)[0]
    print(f"🔍 Requesting Gemini to evaluate invoice: {base}")

    gt_path = os.path.join("ground_truth", file)
    out_path = os.path.join("gemini_output", file)

    if not os.path.exists(out_path):
        results.append([base, "Missing Output", "-", "-", "-"])
        continue

    # Step 1: Read the two JSON files that need to be compared.
    with open(gt_path) as f1, open(out_path) as f2:
        gt = json.load(f1)
        out = json.load(f2)

    # Step 2: Build the prompt containing the data from both files.
    prompt = build_prompt(gt, out, deal_breakers, base)

    try:
        # Step 3: Send the prompt and get Gemini's verdict.
        res = model.generate_content(prompt)
        cleaned_text = res.text.strip().removeprefix("```json").removesuffix("```").strip()
        
        # Step 4: Parse Gemini's verdict JSON.
        eval_data = json.loads(cleaned_text)

        status = eval_data.get("overall_status", "Parse Error")

        # Step 5: Report the verdict in the results list.
        if status == "Pass":
            results.append([base, "Pass", "-", "-", "-"])
        elif status == "Mismatch":
            mismatches = eval_data.get("mismatches", [])
            if not mismatches:
                results.append([base, "Mismatch", "Unknown", "Gemini reported a mismatch but did not provide details", "-"])
            else:
                for mismatch in mismatches:
                    results.append([
                        base,
                        "Mismatch",
                        mismatch.get("field", "N/A"),
                        mismatch.get("expected", "N/A"),
                        mismatch.get("actual", "N/A")
                    ])
        else:
            results.append([base, "Error", "Invalid Status", f"Gemini returned status: {status}", "-"])

    except json.JSONDecodeError:
        print(f"  -> Error: Gemini did not return a valid JSON verdict for {base}.")
        results.append([base, "Error", "Invalid JSON Verdict", res.text, "-"])
    except Exception as e:
        print(f"  -> Gemini Error for {base}: {e}")
        results.append([base, "Error", "API or other Error", str(e), "-"])

# --- 4. EXPORT RESULTS ---
df = pd.DataFrame(results, columns=["Invoice", "Overall Status", "Field", "Expected", "Actual"])
df.to_excel("gemini_evaluation_report.xlsx", index=False)
print("\n✅ Saved to gemini_evaluation_report.xlsx")
