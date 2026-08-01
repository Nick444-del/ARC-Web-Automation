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
def process_exsim_automation(master_csv_path, plant_csv_path, vouchers_dir, base_dir, session_id, include_unmerged=False, remove_first_page=True):
    """
    Yields progress strings. 
    At the end, yields a dict with the path to the final zip file.
    """
    try:
        yield "Starting exsim automation process..."
        work_dir = os.path.join(tempfile.gettempdir(), f"exsim_{session_id}")
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
        data_df = data_df.dropna(how='all')
        data_df = clean_columns(data_df)
        data_df = data_df.apply(lambda col: col.map(safe_str))

        plant_df = read_csv_safe(plant_csv_path)
        plant_df = plant_df.dropna(how='all')
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
        template = env.get_template("exsim_template.html")

        # Process each row
        generated_count = 0
        merged_count = 0

        for index, row in merged_df.iterrows():
            try:
                row_data = {k: safe_str(v) for k, v in row.to_dict().items()}
                
                # Calculate amounts dynamically after updating mapping


                # Additional mappings
                row_data.update({
                    'plant_name': row_data.get('plant_PLANT NAME', row_data.get(plant_col, '')),
                    'plant_address': row_data.get('plant_Address', ''),
                    'plant_gst': row_data.get('plant_GST No', ''),
                    'plant_customer_id': row_data.get('plant_Customer ID', ''),
                    'Total_Billing_to_DK': row_data.get('Total Billing to DK', ''),
                    'Voucher_no': row_data.get('Voucher_no', ''),
                    'Voucher_Type': row_data.get('Voucher Type', ''),
                    'Other_References': row_data.get('Other_References', row_data.get('Other References', row_data.get('Other Reference', ''))),
                    'Reference_No_and_Date': row_data.get('Reference Date', row_data.get('Reference No. & Date', row_data.get('Reference No & Date', row_data.get('Voucher Type', '')))),
                    'Port_of_Loading': row_data.get('Port of Loading', ''),
                    'Port_of_Discharge': row_data.get('Port of Discharge', ''),
                    'place_of_receipt': row_data.get('Place of Receipt by Shipper', row_data.get('Place of Receipt By Shipper', '')),
                    'container_no': row_data.get('Container No.', row_data.get('Container No', row_data.get('container_no', ''))),
                    'container_type': row_data.get('Container Type', row_data.get('container_type', '')),
                    'dispatch_doc_no': row_data.get('Dispatch Doc No.', row_data.get('Dispatch Doc No', row_data.get('despatch_doc_no', ''))),
                    'dispatch_through': row_data.get('Dispatched through', row_data.get('Dispatch Through', row_data.get('Despatch Through', ''))),
                    'bill_of_lading': row_data.get('Bill of Lading/LR-RR No.', row_data.get('Bill of Lading/LR-RR No', row_data.get('Bill of Lading', ''))),
                    'ocean_freight_charges': row_data.get('Ocean Freight Charges', row_data.get('Ocen Freight Charges', '')),
                    'ocean_freight_desc': row_data.get('Ocean Freight Description', row_data.get('Ocean Freight Desc', row_data.get('Ocen Freight Description', ''))),
                    'ocean_freight_cgst': row_data.get('CGST (Ocean Freight Charges) @ 2.50%', row_data.get('CGST (Ocen Freight Charges) @ 2.50%', '')),
                    'ocean_freight_sgst': row_data.get('SGST (Ocean Freight Charges) @ 2.50%', row_data.get('SGST (Ocen Freight Charges) @ 2.50%', '')),
                    'ocean_freight_igst': row_data.get('IGST (Ocean Freight Charges) @ 5%', row_data.get('IGST (Ocen Freight Charges) @ 5%', '')),
                    'carrier_local_charges': row_data.get('Carrier Local Charges', ''),
                    'carrier_local_cgst': row_data.get('CGST (Carrier Local Charges) @ 9%', ''),
                    'carrier_local_sgst': row_data.get('SGST (Carrier Local Charges) @ 9%', ''),
                    'carrier_local_igst': row_data.get('IGST (Carrier Local Charges) @ 18%', ''),
                    'wowtruck_handling_charges': row_data.get('Wowtruck Handling Charges 25 $ Per Container', row_data.get('Wowtruck Handling Charges 25 Per Container', '')),
                    'wowtruck_handling_cgst': row_data.get('CGST (Wowtruck Handling Charges 25 $ Per Container) @ 9%', row_data.get('CGST (Wowtruck Handling Charges 25 Per Container) @ 9%', '')),
                    'wowtruck_handling_sgst': row_data.get('SGST (Wowtruck Handling Charges 25 $ Per Container) @ 9%', row_data.get('SGST (Wowtruck Handling Charges 25 Per Container) @ 9%', '')),
                    'wowtruck_handling_igst': row_data.get('IGST (Wowtruck Handling Charges 25 $ Per Container) @ 18%', row_data.get('IGST (Wowtruck Handling Charges 25 Per Container) @ 18%', '')),
                    'Detention': row_data.get('Detention', ''),
                    'Loading_charges': row_data.get('Loading Charges', ''),
                    'additional_cost': row_data.get('Additional Cost', ''),
                    'Narration': row_data.get('Narration', ''),
                    'address': row_data.get('address', ''),
                    'gstin_uin': row_data.get('gstin_uin', ''),
                    'Particulars1': row_data.get('plant_Particulars1', ''),
                    'vessel_flight_no': row_data.get('Vessel/Flight No.', ''),
                    'Trans_Form': row_data.get('Trasn Form', ''),
                    'Unloading_charges': next((v for k, v in row_data.items() if 'unload' in str(k).lower()), ''),
                    'Additional_Toll': row_data.get('Additional Toll', ''),
                    'Addiotional_Cost_Info': row_data.get('Addiotional Cost Info', ''),
                    'dsc_path': os.path.join(base_dir, 'DSC.png'),  # Included just in case
                    'dsc_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # Dynamically calculate total amount from mapped charge fields
                def parse_amt(val):
                    try:
                        v = str(val).replace(',', '').replace('₹', '').strip()
                        return float(v) if v else 0.0
                    except:
                        return 0.0
                
                charge_keys = [
                    'ocean_freight_charges', 'ocean_freight_cgst', 'ocean_freight_sgst', 'ocean_freight_igst',
                    'carrier_local_charges', 'carrier_local_cgst', 'carrier_local_sgst', 'carrier_local_igst',
                    'wowtruck_handling_charges', 'wowtruck_handling_cgst', 'wowtruck_handling_sgst', 'wowtruck_handling_igst'
                ]
                
                calculated_total = sum(parse_amt(row_data.get(k, 0)) for k in charge_keys)
                
                # Format to integer if no decimals needed, else 2 decimal places
                row_data['Total_Amount'] = f"{calculated_total:.2f}".rstrip('0').rstrip('.') if calculated_total % 1 != 0 else f"{int(calculated_total)}"
                
                try:
                    row_data['Total_Amount_words'] = amount_to_words(calculated_total)
                except:
                    row_data['Total_Amount_words'] = "Zero Only"

                invoice_no = str(row_data.get('invoice_no', row_data.get('Invoice No', row_data.get('Invoice No.', f"INV_{index}")))).strip().replace('/', '-')
                if not invoice_no or invoice_no.lower() == 'nan': invoice_no = f"INV_{index}"
                row_data['invoice_no'] = invoice_no
                
                # 3. Generate HTML & PDF
                html_content = template.render(**row_data)
                invoice_pdf_path = os.path.join(invoices_dir, f"{invoice_no}.pdf")
                
                HTML(string=html_content, base_url=base_dir).write_pdf(invoice_pdf_path)
                generated_count += 1
                
                # 4. Merge PDF using Reference No. (Voucher_no column)
                reference_no_raw = row_data.get('Voucher_no', '')
                merged_successfully = False
                
                if reference_no_raw:
                    ref_parts = str(reference_no_raw).split("/")
                    if len(ref_parts) >= 3:
                        ref_key = " ".join(ref_parts[:3]).upper()
                        voucher_path = voucher_files.get(ref_key)
                        
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
                                yield f"✅ Merged invoice {invoice_no} with reference {ref_key}"
                            except Exception as e:
                                yield f"❌ Error merging row {index+1} ({invoice_no}): {e}"
                        else:
                            yield f"⚠️ Voucher PDF not found for Reference No: {ref_key} (Row {index+1})"
                    else:
                        yield f"⚠️ Unexpected Reference No. format '{reference_no_raw}' at row {index+1}"
                else:
                    yield f"⚠️ Missing Reference No. at row {index+1}"
                    
                if include_unmerged and not merged_successfully:
                    shutil.copy2(invoice_pdf_path, os.path.join(unmerged_dir, f"{invoice_no}_unmerged.pdf"))

            except Exception as e:
                yield f"❌ Error processing row {index + 1}: {str(e)}"
                
        yield f"Generated {generated_count} invoices, merged {merged_count} successfully."
        
        # 5. Create ZIP
        yield "Creating final zip file..."
        zip_filename = f"exsim_merged_invoices_{session_id}.zip"
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
