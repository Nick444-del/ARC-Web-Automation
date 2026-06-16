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
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert(n):
        if n < 10: return units[n]
        if n < 20: return teens[n - 10]
        if n < 100: return tens[n // 10] + (" " + units[n % 10] if n % 10 else "")
        if n < 1000: return units[n // 100] + " Hundred" + (" " + convert(n % 100) if n % 100 else "")
        if n < 100000: return convert(n // 1000) + " Thousand" + (" " + convert(n % 1000) if n % 1000 else "")
        if n < 10000000: return convert(n // 100000) + " Lakh" + (" " + convert(n % 100000) if n % 100000 else "")
        return convert(n // 10000000) + " Crore" + (" " + convert(n % 10000000) if n % 10000000 else "")

    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    result = convert(rupees)
    if paise: result += f" and {convert(paise)} Paise"
    return result + " Only"

# ============================================================
# AUTOMATION GENERATOR
# ============================================================
def process_automation(master_csv_path, plant_csv_path, vouchers_dir, base_dir, session_id, include_unmerged=False):
    """
    Yields progress strings. 
    At the end, yields a dict with the path to the final zip file.
    """
    try:
        yield "Starting automation process..."
        
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
        template = env.get_template("template.html")

        # Setup Directories
        work_dir = os.path.join(tempfile.gettempdir(), f"arc_{session_id}")
        invoices_dir = os.path.join(work_dir, "invoices")
        merged_pdfs_dir = os.path.join(work_dir, "merged_pdfs")
        
        os.makedirs(invoices_dir, exist_ok=True)
        os.makedirs(merged_pdfs_dir, exist_ok=True)

        # Index voucher files (uppercase name -> path)
        voucher_files = {}
        for f in os.listdir(vouchers_dir):
            if f.lower().endswith('.pdf'):
                name_no_ext = os.path.splitext(f)[0].strip().upper()
                voucher_files[name_no_ext] = os.path.join(vouchers_dir, f)

        # Process each row
        for index, row in merged_df.iterrows():
            try:
                data = {str(k): safe_str(v) for k, v in row.to_dict().items()}
                
                # Basic Mapping
                data["consignee_name"] = data.get("Cnee Name")
                data["address"] = data.get("Address")
                data["Bill_no"] = data.get("Bill No")
                data["Bill_date"] = data.get("Bill Dt")
                data["Product_code"] = data.get("Product Code")
                data["Invoice_value"] = data.get("Invoice Value")
                data["CnNo"] = data.get("CnNo")
                data["Cn_Booking_Date"] = data.get("Cn Booking Date")
                data["no_of_packages"] = data.get("No Of Pkgs")
                data["actual_weight"] = data.get("Actual Wt")
                data["charge_wt"] = data.get("Charge Wt")
                data["Dom_No"] = data.get("Dom No")
                data["Pickup"] = data.get("Pick up")
                data["Drop"] = data.get("Drop")

                # Charges
                data["Freight"] = data.get("Freight", "")
                data["LR"] = data.get("LR", "")
                data["DD"] = data.get("DD", "")
                data["GC"] = data.get("GC", "")
                data["AOC"] = data.get("AOC", "")
                data["ODA"] = data.get("ODA", "")
                data["local_charges"] = data.get("local charge") or data.get("Local Charge") or data.get("Local charge") or ""
                data["sell_rate"] = data.get("Sell Rate", "")
                data["other_charges"] = data.get("other charges") or data.get("Other Charges") or data.get("Other charges") or ""
                data["toll_charge"] = data.get("Toll Charge") or data.get("toll charge") or data.get("Toll charge") or ""
                data["unloading"] = data.get("Unloading") or data.get("unloading") or data.get("Unloading Charges") or ""
                data["special_delivery_charge"] = data.get("Special Delivery Charge") or data.get("special delivery charge") or data.get("Special delivery charge") or ""

                # Plant Details
                data["plant_address"] = data.get("plant_Address")
                data["plant_gst"] = data.get("plant_GST No")
                data["plant_customer_id"] = data.get("plant_Customer ID")

                data["Invoice_Dt"] = datetime.now().strftime("%d-%m-%Y")

                # Invoice Name
                invoice_name = ""
                try:
                    invoice_name = safe_str(row.iloc[42])
                except:
                    pass
                if not invoice_name: invoice_name = f"Invoice_{index + 1}"
                
                for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    invoice_name = invoice_name.replace(ch, "_")
                data["invoice_no"] = invoice_name

                # Totals
                subtotal = (
                    safe_float(data.get("Freight")) + safe_float(data.get("LR")) +
                    safe_float(data.get("DD")) + safe_float(data.get("GC")) +
                    safe_float(data.get("AOC")) + safe_float(data.get("ODA")) +
                    safe_float(data.get("local_charges")) + safe_float(data.get("other_charges")) +
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
                invoice_path = os.path.join(invoices_dir, f"{invoice_name}.pdf")
                HTML(string=html, base_url=base_dir).write_pdf(invoice_path)
                
                yield f"✅ Generated invoice: {invoice_name}"

                # Merge PDF logic
                invoice_no_upper = str(invoice_name).strip().upper()
                cn_no = str(data.get('CnNo', '')).strip().upper()
                bill_no = str(data.get('Bill_no', '')).strip().upper()
                
                voucher_path = None
                if cn_no and cn_no != 'NAN':
                    voucher_path = voucher_files.get(cn_no)
                if not voucher_path and bill_no and bill_no != 'NAN':
                    voucher_path = voucher_files.get(bill_no)

                if voucher_path:
                    merger = PdfMerger()
                    merger.append(invoice_path)
                    merger.append(voucher_path)
                    
                    output_name = f"{invoice_name}.pdf"
                    output_path = os.path.join(merged_pdfs_dir, output_name)
                    merger.write(output_path)
                    merger.close()
                    yield f"✅ Merged with voucher: {os.path.basename(voucher_path)}"
                else:
                    if include_unmerged:
                        yield f"⚠️ No voucher found for {invoice_name}. Including unmerged invoice."
                        shutil.copy(invoice_path, os.path.join(merged_pdfs_dir, f"{invoice_name}.pdf"))
                    else:
                        yield f"⚠️ Skipped: No voucher found for {invoice_name} (CnNo: {cn_no}, Bill No: {bill_no})"

            except Exception as e:
                yield f"❌ Error on row {index + 1}: {e}"

        # Zip files
        yield "Creating final zip package..."
        zip_path = os.path.join(tempfile.gettempdir(), f"Completed_Invoices_{session_id}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(merged_pdfs_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), file)

        yield "✅ Automation complete!"
        yield {"zip_path": zip_path}

    except Exception as e:
        yield f"❌ Fatal Error: {e}"
