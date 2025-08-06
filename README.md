---
title: "Invoice Extraction Asset"
description: "A pipeline to automatically route, extract, and evaluate structured invoice data using Gemini 2.5 Pro."
author: "Aman Usmani"
year: "2025"
license: "MIT"
repository: "https://github.com/Amanusmani242/invoice_Extraction.git"
---

# 📌 Features
- Invoice Routing based on seller name
- Structured JSON Extraction via LLM
- Strict deal-breaker-based Evaluation
- Supports PDF, Image, Excel, CSV formats

# 🗂️ Project Structure


input_invoices/        - Incoming raw invoices  
sorted_invoices/       - Invoices organized by seller_name  
gemini_output/         - Structured JSON results  
ground_truth/          - Manually verified invoice data  
error_invoices/        - Files that failed during processing  
router.py              - Seller-based routing using Gemini  
extractor.py           - Gemini-based structured data extraction  
evaluator.py           - Field-level evaluation against ground truth  
config.yaml            - Configurable list of critical fields (deal-breakers)  

# Architecture

input_invoices/ --> router.py --> sorted_invoices/<seller>/
                         |
                         v
                  extractor.py --> gemini_output/
                         |
                         v
                  evaluator.py --> gemini_evaluation_report.xlsx

# ⚙️ Setup
## 📦 Requirements
Python 3.8+

google-generativeai

pandas

openpyxl

python-dotenv

pyyaml

## 🔐 Environment Variables
Create a .env file:env

GEMINI_API_KEY=your_gemini_api_key

## 🛠️ Run Pipeline
python router.py      # Route invoices by seller name
python extractor.py   # Extract structured JSON using Gemini
python evaluator.py   # Compare extracted vs. ground truth

## ⚙️ Config (Deal-Breaker Fields)
## config.yaml
deal_breakers:
  - invoice.invoice_number
  - invoice.invoice_date
  - payment_instructions.account_number
  - subtotal.total



