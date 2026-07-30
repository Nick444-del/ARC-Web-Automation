# 🧾 ARC Invoice Automation Web App

A full-stack web application that automates the generation and processing of invoices for multiple business units — **ARC**, **V-Trans**, **HMC**, and **EXSIM**. Upload your CSV data and PDF vouchers, and the system generates merged, ready-to-send invoice PDFs in seconds with real-time progress tracking.

🌐 **Live App**: [arc-web-automation.vercel.app](https://arc-web-automation.vercel.app)

---

## ✨ Features

- **4 Invoice Types** — Dedicated automation pipelines for ARC, V-Trans, HMC, and EXSIM invoices
- **Real-Time Progress Console** — Live WebSocket-powered console shows step-by-step generation logs
- **Drag & Drop Uploads** — Intuitive file upload interface for Master CSVs and PDF vouchers
- **Smart PDF Merging** — Automatically merges generated invoices with their corresponding voucher PDFs
- **Bulk ZIP Download** — All processed files packaged into a single downloadable ZIP
- **Dark / Light Mode** — Toggle between themes, preference saved across sessions
- **Responsive Sidebar** — Collapsible navigation with unique icons per invoice type
- **404 Refresh Fix** — `vercel.json` rewrite rules ensure SPA routes work correctly on page refresh

---

## 🛠️ Tech Stack

### Frontend
| Tech | Purpose |
|---|---|
| **React 19 + Vite** | UI framework and build tool |
| **Tailwind CSS** | Utility-first styling |
| **Framer Motion** | Smooth animations |
| **React Router DOM** | Client-side routing |
| **react-dropzone** | Drag & drop file uploads |
| **Axios** | HTTP requests to the backend |
| **lucide-react** | Icon library |

### Backend
| Tech | Purpose |
|---|---|
| **FastAPI** | Python web framework for REST + WebSocket APIs |
| **Uvicorn** | ASGI server |
| **Pandas** | CSV parsing and data manipulation |
| **Jinja2** | HTML invoice template rendering |
| **WeasyPrint** | HTML-to-PDF conversion |
| **PyPDF2** | PDF merging and page manipulation |

---

## 📂 Project Structure

```
ARC-Web-Automation/
├── backend/
│   ├── main.py                  # FastAPI entry point — all API & WebSocket routes
│   ├── automation.py            # ARC invoice automation logic
│   ├── vtrans_automation.py     # V-Trans invoice automation logic
│   ├── hmc_automation.py        # HMC invoice automation logic
│   ├── exsim_automation.py      # EXSIM invoice automation logic
│   ├── template.html            # Jinja2 HTML template for ARC invoices
│   ├── vtrans_template.html     # Jinja2 HTML template for V-Trans invoices
│   ├── hmc_template.html        # Jinja2 HTML template for HMC invoices
│   ├── exsim_template.html      # Jinja2 HTML template for EXSIM invoices
│   ├── plant_data.csv           # Plant/customer reference data
│   ├── logo.jpg                 # Company logo used in invoice headers
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Docker config for backend deployment
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root app with router setup
│   │   ├── ArcApp.jsx           # ARC invoice upload & generation page
│   │   ├── VTransApp.jsx        # V-Trans invoice upload & generation page
│   │   ├── HmcApp.jsx           # HMC invoice upload & generation page
│   │   ├── ExsimApp.jsx         # EXSIM invoice upload & generation page
│   │   └── components/
│   │       ├── Sidebar.jsx      # Collapsible sidebar with nav links & theme toggle
│   │       └── ProgressTracker.jsx  # Real-time console log display
│   ├── public/
│   │   ├── sample_master.csv    # Sample master CSV for ARC
│   │   ├── sample_vtrans.csv    # Sample CSV for V-Trans
│   │   ├── sample_hmc.csv       # Sample CSV for HMC
│   │   └── sample_exsim.csv     # Sample CSV for EXSIM
│   ├── vercel.json              # Vercel SPA rewrite rules (fixes 404 on refresh)
│   └── package.json             # Node.js dependencies
│
├── vercel.json                  # Root Vercel config
└── run_app.bat                  # Windows batch script to start both servers
```

---

## 📋 Prerequisites

Make sure the following are installed on your machine:

- **Node.js** v18 or higher — [nodejs.org](https://nodejs.org)
- **Python** v3.9 or higher — [python.org](https://python.org)
- **pip** (comes with Python)

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Nick444-del/ARC-Web-Automation.git
cd ARC-Web-Automation
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # On Windows
# source venv/bin/activate   # On macOS/Linux
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

---

## 🚀 Running the Application

### ⚡ Quick Start (Windows Only)
From the root directory, run the provided batch script which starts both servers simultaneously:
```bash
run_app.bat
```

### Manual Start

**Backend** (runs on `http://localhost:8000`):
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Frontend** (runs on `http://localhost:5173`):
```bash
cd frontend
npm run dev
```

Then open your browser and go to: **http://localhost:5173**

---

## 📖 How to Use

1. **Select Invoice Type** — Click on the desired invoice type in the sidebar (ARC, V-Trans, HMC, or EXSIM)
2. **Download Sample CSV** — Use the sample CSV link on the page to see the expected column format
3. **Upload Master CSV** — Drag & drop or browse to upload your filled-in data CSV
4. **Upload Voucher PDFs** — Upload all the corresponding PDF vouchers for matching
5. **Generate** — Click the **Generate Invoices** button and watch the real-time console
6. **Download** — Once complete, download the ZIP file containing all merged PDFs

---

## 📄 CSV Column Reference

Each invoice type has its own CSV format. Download the sample files from the app for the exact headers. Key columns per type:

| Type | Key Columns |
|---|---|
| **ARC** | `date`, `Particulars`, `invoice_no`, `PLANT`, `CGST`, `SGST`, `IGST`, `Total Amount` |
| **V-Trans** | `date`, `Particulars`, `Voucher_no`, `PLANT`, `invoice_no`, `Total Amount` |
| **HMC** | `date`, `Particulars`, `Voucher_no`, `PLANT`, `Ocean Freight Charges`, `Carrier Local Charges` |
| **EXSIM** | `date`, `Voucher_no`, `PLANT`, `Ocean Freight Charges`, `Carrier Local Charges`, `Wowtruck Handling Charges 25 Per Container`, `Total Amount` |

---

## 🏗️ Architecture Overview

```
Browser (React SPA)
       │
       ├── REST API (POST /generate-*)  ──► FastAPI Backend
       │                                        │
       └── WebSocket (/ws/*)  ◄────────── Real-time progress stream
                                                │
                                         Pandas (CSV parsing)
                                                │
                                         Jinja2 (HTML rendering)
                                                │
                                         WeasyPrint (HTML → PDF)
                                                │
                                         PyPDF2 (PDF merging)
                                                │
                                         ZIP → download response
```

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📜 License

This project is private and intended for internal business use.
