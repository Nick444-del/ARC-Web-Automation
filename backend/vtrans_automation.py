import os
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime
from PyPDF2 import PdfMerger
import zipfile
import tempfile
import shutil

# ============================================================
# UTILITIES
# ============================================================
def clean_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
        .str.replace("\xa0", "", regex=False)
    )
    return df

def safe_str(val):
    if pd.isna(val): return ""
    cleaned = str(val).replace("\xa0", " ").strip()
    if cleaned.lower() in ["none", "nan"]: return ""
    return cleaned

def safe_float(val):
    try:
        return float(str(val).replace(",", "").replace("₹", "").strip())
    except:
        return 0.0

def read_csv_safe(path):
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except Exception:
            continue
    raise Exception("Unable to read CSV")

def amount_to_words(amount):
    try:
        amount = float(amount)
    except:
        return "Zero Only"

    if amount == 0: return "Zero Only"
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    scales = ["", "Thousand", "Lakh", "Crore"]

    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))

    def convert(n):
        if n < 10: return units[n]
        if n < 20: return teens[n - 10]
        if n < 100: return tens[n // 10] + (" " + units[n % 10] if n % 10 else "")
        return units[n // 100] + " Hundred" + (" " + convert(n % 100) if n % 100 else "")

    words = []
    scale = 0

    while rupees > 0:
        chunk = rupees % 1000 if scale == 0 else rupees % 100
        if chunk:
            words.insert(0, convert(chunk) + (" " + scales[scale] if scales[scale] else ""))
        rupees = rupees // 1000 if scale == 0 else rupees // 100
        scale += 1

    result = " ".join(words).strip()
    if paise:
        result += f" and {convert(paise)} Paise"

    return result + " Only"

# ============================================================
# AUTOMATION GENERATOR
# ============================================================
def process_vtrans_automation(master_csv_path, plant_csv_path, vouchers_dir, base_dir, session_id, include_unmerged=False):
    """
    Yields progress strings. 
    At the end, yields a dict with the path to the final zip file.
    """
    try:
        yield "Starting V-Trans automation process..."
        
        # Load Data
        yield "Loading CSV data..."
        data_df = read_csv_safe(master_csv_path)
        data_df = clean_columns(data_df)
        data_df = data_df.apply(lambda col: col.map(safe_str))

        plant_df = read_csv_safe(plant_csv_path)
        plant_df = clean_columns(plant_df)
        plant_df = plant_df.apply(lambda col: col.map(safe_str))

        if "Particlar1" in plant_df.columns:
            plant_df.rename(columns={"Particlar1": "Particulars1"}, inplace=True)

        data_df["PLANT"] = data_df["PLANT"].astype(str).str.split(".").str[0].str.strip()
        plant_df["Customer ID"] = plant_df["Customer ID"].astype(str).str.strip()
        plant_df = plant_df.add_prefix("plant_")

        merged_df = pd.merge(data_df, plant_df, left_on="PLANT", right_on="plant_Customer ID", how="left")
        
        yield f"Data loaded successfully. {len(merged_df)} rows found."

        # Setup Template
        env = Environment(loader=FileSystemLoader(base_dir))
        template = env.get_template("vtrans_template.html")

        # Setup Directories
        work_dir = os.path.join(tempfile.gettempdir(), f"vtrans_{session_id}")
        invoices_dir = os.path.join(work_dir, "invoices")
        merged_pdfs_dir = os.path.join(work_dir, "merged_pdfs")
        
        os.makedirs(invoices_dir, exist_ok=True)
        os.makedirs(merged_pdfs_dir, exist_ok=True)

        # Process each row
        for index, row in merged_df.iterrows():
            try:
                data = {str(k): safe_str(v) for k, v in row.to_dict().items()}
                
                # Mapping based on generate_weasy.py logic
                data["consignee_name"] = data.get("Cnee Name")
                data["pickup_address"] = data.get("Address")
                data["Dorf_no"] = data.get("Dorf No") or data.get("Invoice No")
                data["Product_code"] = data.get("Product Code")
                data["pickup"] = data.get("Pick up")
                data["Drop"] = data.get("Drop")
                data["Actual_Wt"] = data.get("Actual Wt")
                data["Sell_Rate"] = data.get("Sell Rate")

                # Charges
                data["Freight"] = data.get("Freight", "")
                data["LR"] = data.get("LR", "")
                data["DD"] = data.get("DD", "")
                data["GC"] = data.get("GC", "")
                data["Taxable_Amt"] = data.get("Taxable Amt")

                data["AOC"] = data.get("AOC") or data.get(" AOC ") or ""
                data["special_delivery_charge"] = data.get("special delivery charge") or data.get(" special delivery charge ") or ""
                data["ODA"] = data.get("ODA") or data.get(" ODA ") or ""
                data["local_charges"] = data.get("local charge") or data.get(" local charge ") or ""
                data["unloading"] = data.get("Unloading at client location") or data.get(" Unloading at client location ") or ""
                data["toll_charge"] = data.get("Toll charges") or data.get(" Toll charges ") or data.get("Toll Charge") or data.get(" Toll Charge ") or ""

                # Plant info
                data["plant_address"] = data.get("plant_Address")
                data["plant_gst"] = data.get("plant_GST No")
                data["plant_customer_id"] = data.get("plant_Customer ID")

                current_date = datetime.now()
                month = current_date.strftime("%m")
                year = current_date.strftime("%y")
                
                # Check custom Invoice No overriding from user specification
                custom_invoice_no = data.get("Invoice No")
                if custom_invoice_no and str(custom_invoice_no).lower() != "nan" and str(custom_invoice_no).strip() != "":
                    invoice_no = str(custom_invoice_no).strip()
                else:
                    series_number = 70001 + index
                    invoice_no = f"WT{month}{year}{series_number}"
                    
                for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    invoice_no = invoice_no.replace(ch, "_")

                data["Invoice_Dt"] = current_date.strftime("%d-%m-%Y")
                data["invoice_no"] = invoice_no

                # Totals
                subtotal = (
                    safe_float(data.get("Freight")) + safe_float(data.get("LR")) +
                    safe_float(data.get("DD")) + safe_float(data.get("GC")) +
                    safe_float(data.get("AOC")) + safe_float(data.get("ODA")) +
                    safe_float(data.get("local_charges")) +
                    safe_float(data.get("toll_charge")) + safe_float(data.get("unloading")) +
                    safe_float(data.get("special_delivery_charge"))
                )
                gst = subtotal * 0.18
                total_amount = subtotal + gst
                data["subtotal_amount"] = f"{subtotal:.2f}"
                data["GST"] = f"{gst:.2f}"
                data["Total_Amount"] = f"{total_amount:.2f}"
                data["Total_Amount_words"] = amount_to_words(total_amount)

                # Generate PDF
                html = template.render(**data)
                invoice_path = os.path.join(invoices_dir, f"{invoice_no}.pdf")
                HTML(string=html, base_url=base_dir).write_pdf(invoice_path)
                
                yield f"✅ Generated invoice: {invoice_no}"

                # Merge PDF logic
                merge_docs = str(data.get("Merge Doc", "")).strip()
                
                if not merge_docs or merge_docs.lower() == "nan":
                    if include_unmerged:
                        yield f"⚠️ No merge docs specified for {invoice_no}. Including unmerged invoice."
                        shutil.copy(invoice_path, os.path.join(merged_pdfs_dir, f"{invoice_no}.pdf"))
                    else:
                        yield f"⚠️ Skipped: No Merge Doc specified for {invoice_no}"
                    continue
                
                if "," in merge_docs:
                    files = merge_docs.split(",")
                elif "|" in merge_docs:
                    files = merge_docs.split("|")
                else:
                    files = merge_docs.split()

                files = [f.strip() for f in files if f.strip()]
                
                merger = PdfMerger()
                merger.append(invoice_path)
                
                added_any = False
                for file_name in files:
                    if file_name.lower() == "nan": continue
                    
                    file_pdf = file_name if file_name.lower().endswith(".pdf") else file_name + ".pdf"
                    exact_path = os.path.join(vouchers_dir, file_pdf)
                    
                    if os.path.exists(exact_path):
                        merger.append(exact_path)
                        added_any = True
                        continue
                        
                    # Partial match
                    matched = None
                    for f in os.listdir(vouchers_dir):
                        if file_name in f:
                            matched = f
                            break
                            
                    if matched:
                        merger.append(os.path.join(vouchers_dir, matched))
                        added_any = True
                    else:
                        yield f"⚠️ Could not find voucher file: {file_name}"
                        
                if added_any:
                    output_name = f"{invoice_no}.pdf"
                    output_path = os.path.join(merged_pdfs_dir, output_name)
                    merger.write(output_path)
                    merger.close()
                    yield f"✅ Merged {invoice_no} with {len(files)} vouchers"
                else:
                    merger.close()
                    if include_unmerged:
                        yield f"⚠️ Vouchers not found for {invoice_no}. Including unmerged invoice."
                        shutil.copy(invoice_path, os.path.join(merged_pdfs_dir, f"{invoice_no}.pdf"))
                    else:
                        yield f"⚠️ Skipped: Vouchers not found for {invoice_no}"

            except Exception as e:
                yield f"❌ Error on row {index + 1}: {e}"

        # Zip files
        yield "Creating final zip package..."
        zip_path = os.path.join(tempfile.gettempdir(), f"Completed_VTrans_Invoices_{session_id}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(merged_pdfs_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), file)

        yield "✅ Automation complete!"
        yield {"zip_path": zip_path}

    except Exception as e:
        yield f"❌ Fatal Error: {str(e)}"
