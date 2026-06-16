import os
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime
import PyPDF2
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
def process_hmc_automation(master_csv_path, plant_csv_path, vouchers_dir, base_dir, session_id, include_unmerged=False, remove_first_page=True):
    """
    Yields progress strings. 
    At the end, yields a dict with the path to the final zip file.
    """
    try:
        yield "Starting HMC automation process..."
        work_dir = os.path.join(tempfile.gettempdir(), f"hmc_{session_id}")
        invoices_dir = os.path.join(work_dir, "invoices")
        merged_pdfs_dir = os.path.join(work_dir, "merged_pdfs")
        processed_vouchers_dir = os.path.join(work_dir, "processed_vouchers")
        unmerged_dir = os.path.join(work_dir, "unmerged_invoices")
        
        os.makedirs(invoices_dir, exist_ok=True)
        os.makedirs(merged_pdfs_dir, exist_ok=True)
        os.makedirs(processed_vouchers_dir, exist_ok=True)
        os.makedirs(unmerged_dir, exist_ok=True)

        # 1. Process Vouchers (Remove First Page optionally)
        yield "Processing voucher PDFs..."
        for filename in os.listdir(vouchers_dir):
            if filename.lower().endswith(".pdf"):
                input_path = os.path.join(vouchers_dir, filename)
                output_path = os.path.join(processed_vouchers_dir, filename)
                
                if remove_first_page:
                    try:
                        with open(input_path, 'rb') as infile:
                            reader = PyPDF2.PdfReader(infile)
                            writer = PyPDF2.PdfWriter()
                            if len(reader.pages) <= 1:
                                yield f"⚠️ Skipping removing page from '{filename}' (has only 1 page)"
                                shutil.copy2(input_path, output_path)
                            else:
                                for page_num in range(1, len(reader.pages)):
                                    writer.add_page(reader.pages[page_num])
                                with open(output_path, 'wb') as outfile:
                                    writer.write(outfile)
                    except Exception as e:
                        yield f"❌ Error removing first page from {filename}: {e}"
                        shutil.copy2(input_path, output_path) # Fallback
                else:
                    shutil.copy2(input_path, output_path)
                    
        # Load processed voucher files map
        voucher_files = {os.path.splitext(f)[0].strip().upper(): os.path.join(processed_vouchers_dir, f)
                         for f in os.listdir(processed_vouchers_dir) if f.lower().endswith('.pdf')}

        # 2. Load Data
        yield "Loading CSV data..."
        data_df = read_csv_safe(master_csv_path)
        data_df = clean_columns(data_df)
        data_df = data_df.apply(lambda col: col.map(safe_str))

        plant_df = read_csv_safe(plant_csv_path)
        plant_df = clean_columns(plant_df)
        plant_df = plant_df.apply(lambda col: col.map(safe_str))

        if "Particlar1" in plant_df.columns:
            plant_df.rename(columns={"Particlar1": "Particulars1"}, inplace=True)

        # Process PLANT column
        plant_col = [col for col in data_df.columns if 'PLANT' in col.upper()]
        if plant_col:
            plant_col = plant_col[0]
            data_df[plant_col] = data_df[plant_col].astype(str).str.split(".").str[0].str.strip()
        else:
            yield "❌ 'PLANT' column not found in data.csv"
            return

        plant_df["Customer ID"] = plant_df["Customer ID"].astype(str).str.strip()
        plant_df_prefixed = plant_df.add_prefix("plant_")

        merged_df = pd.merge(data_df, plant_df_prefixed, left_on=plant_col, right_on="plant_Customer ID", how="left")
        yield f"Data loaded successfully. {len(merged_df)} rows found."

        # Setup Template
        env = Environment(loader=FileSystemLoader(base_dir))
        template = env.get_template("hmc_template.html")

        # Process each row
        generated_count = 0
        merged_count = 0

        for index, row in merged_df.iterrows():
            try:
                row_data = {k: safe_str(v) for k, v in row.to_dict().items()}
                
                # Amount in words
                try:
                    raw_amount = str(row_data.get('Total Amount', 0) or 0).replace(',', '').replace('₹', '').strip()
                    amount = float(raw_amount) if raw_amount else 0
                    row_data['Total_Amount_words'] = amount_to_words(amount)
                except:
                    row_data['Total_Amount_words'] = "Zero Only"

                # Subtotal
                try:
                    transport = float(row_data.get('Transport', 0) or 0)
                    loading = float(row_data.get('Loading Charges', 0) or 0)
                    detention = float(row_data.get('Detention', 0) or 0)
                    additional = float(row_data.get('Additional Cost', 0) or 0)
                    row_data['sub_total'] = round(transport + loading + detention + additional, 2)
                except:
                    row_data['sub_total'] = 0

                # Additional mappings
                row_data.update({
                    'plant_name': row_data.get('plant_PLANT NAME', row_data.get(plant_col, '')),
                    'plant_address': row_data.get('plant_Address', ''),
                    'plant_gst': row_data.get('plant_GST No', ''),
                    'plant_customer_id': row_data.get('plant_Customer ID', ''),
                    'Total_Amount': row_data.get('Total Amount', ''),
                    'Total_Billing_to_DK': row_data.get('Total Billing to DK', ''),
                    'Voucher_no': row_data.get('Voucher_no', ''),
                    'Voucher_Type': row_data.get('Voucher Type', ''),
                    'Other_Reference': row_data.get('Other_Reference', ''),
                    'Order_No_and_Date': row_data.get('Order_No_&_Date', ''),
                    'Port_of_Loading': row_data.get('Port of Loading', ''),
                    'Port_of_Discharge': row_data.get('Port of Discharge', ''),
                    'dispatch_through': row_data.get('Despatch Through', ''),
                    'Detention': row_data.get('Detention', ''),
                    'Loading_charges': row_data.get('Loading Charges', ''),
                    'additional_cost': row_data.get('Additional Cost', ''),
                    'Narration': row_data.get('Narration', ''),
                    'address': row_data.get('address', ''),
                    'gstin_uin': row_data.get('gstin_uin', ''),
                    'Particulars1': row_data.get('plant_Particulars1', ''),
                    'vessel_flight_no': row_data.get('Vessel/Flight No.', ''),
                    'Trans_Form': row_data.get('Trasn Form', ''),
                    'Unloading_charges': row_data.get('Unloading Charges', ''),
                    'Additional_Toll': row_data.get('Additional Toll', ''),
                    'Addiotional_Cost_Info': row_data.get('Addiotional Cost Info', ''),
                    'dsc_path': os.path.join(base_dir, 'DSC.png'),  # Included just in case
                    'dsc_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                invoice_no = str(row_data.get('invoice_no', f"INV_{index}")).strip().replace('/', '-')
                if not invoice_no: invoice_no = f"INV_{index}"
                
                # 3. Generate HTML & PDF
                html_content = template.render(**row_data)
                invoice_pdf_path = os.path.join(invoices_dir, f"{invoice_no}.pdf")
                
                HTML(string=html_content, base_url=base_dir).write_pdf(invoice_pdf_path)
                generated_count += 1
                
                # 4. Merge PDF
                voucher_raw = row_data.get('Voucher_no', '')
                merged_successfully = False
                
                if voucher_raw:
                    voucher_parts = str(voucher_raw).split("/")
                    if len(voucher_parts) >= 3:
                        voucher_key = " ".join(voucher_parts[:3]).upper()
                        voucher_path = voucher_files.get(voucher_key)
                        
                        if voucher_path:
                            try:
                                merger = PdfMerger()
                                merger.append(invoice_pdf_path)
                                merger.append(voucher_path)
                                
                                merged_pdf_path = os.path.join(merged_pdfs_dir, f"{invoice_no}_merged.pdf")
                                merger.write(merged_pdf_path)
                                merger.close()
                                merged_successfully = True
                                merged_count += 1
                                yield f"✅ Merged invoice {invoice_no} with voucher {voucher_key}"
                            except Exception as e:
                                yield f"❌ Error merging row {index+1} ({invoice_no}): {e}"
                        else:
                            yield f"⚠️ Voucher PDF not found for: {voucher_key} (Row {index+1})"
                    else:
                        yield f"⚠️ Unexpected voucher format '{voucher_raw}' at row {index+1}"
                else:
                    yield f"⚠️ Missing Voucher_no at row {index+1}"
                    
                if include_unmerged and not merged_successfully:
                    shutil.copy2(invoice_pdf_path, os.path.join(unmerged_dir, f"{invoice_no}_unmerged.pdf"))

            except Exception as e:
                yield f"❌ Error processing row {index + 1}: {str(e)}"
                
        yield f"Generated {generated_count} invoices, merged {merged_count} successfully."
        
        # 5. Create ZIP
        yield "Creating final zip file..."
        zip_filename = f"hmc_merged_invoices_{session_id}.zip"
        zip_filepath = os.path.join(tempfile.gettempdir(), zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for folderName, _, filenames in os.walk(merged_pdfs_dir):
                for filename in filenames:
                    file_path = os.path.join(folderName, filename)
                    zipf.write(file_path, arcname=os.path.join("Merged", filename))
                    
            if include_unmerged:
                for folderName, _, filenames in os.walk(unmerged_dir):
                    for filename in filenames:
                        file_path = os.path.join(folderName, filename)
                        zipf.write(file_path, arcname=os.path.join("Unmerged", filename))

        yield {"zip_path": zip_filepath}
        
    except Exception as e:
        yield f"❌ Critical error in automation: {str(e)}"
