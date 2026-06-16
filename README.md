# ARC Invoice Automation Web App

This project is a full-stack web application designed to automate the processing and generation of invoices and vouchers. It consists of a React-based frontend and a FastAPI-based Python backend, providing a seamless user interface for file uploads, real-time progress tracking, and automated document generation.

## 🚀 Features

- **Automated Processing**: Automates the processing for different invoice types (ARC, V-Trans, HMC).
- **Real-Time Progress**: Uses WebSockets to provide real-time feedback and progress updates to the user while documents are being generated.
- **Drag & Drop Uploads**: Easy-to-use file upload interface built with `react-dropzone` for master CSVs and PDF vouchers.
- **Bulk Download**: Automatically zips the processed invoices and allows the user to download them as a single file.

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS, Framer Motion (for animations)
- **Routing**: React Router DOM
- **HTTP/WebSockets**: Axios and native WebSockets

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Concurrency**: `asyncio` for non-blocking file processing and WebSocket communication

## 📂 Project Structure

```
WebApp/
├── backend/                  # FastAPI backend server
│   ├── automation.py         # ARC automation script
│   ├── hmc_automation.py     # HMC automation script
│   ├── vtrans_automation.py  # V-Trans automation script
│   ├── main.py               # FastAPI entry point
│   ├── requirements.txt      # Python dependencies
│   ├── plant_data.csv        # Reference data for automation
│   └── templates...          # HTML templates for PDF generation
│
├── frontend/                 # React frontend application
│   ├── src/                  # React components and pages
│   ├── public/               # Static assets
│   ├── package.json          # Node.js dependencies
│   └── tailwind.config.js    # Tailwind configuration
│
└── run_app.bat               # Batch script to start both frontend and backend
```

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Node.js** (v18 or higher)
- **Python** (v3.9 or higher)

## ⚙️ Installation & Setup

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the dependencies:
   ```bash
   npm install
   ```

## 🚀 Running the Application

### Using the Batch Script (Windows)
The easiest way to start the application on Windows is to run the provided batch script from the root `WebApp/` directory:

```bash
run_app.bat
```
This script will automatically start the FastAPI backend on `http://localhost:8000` and the Vite frontend development server on `http://localhost:5173`.

### Manual Start
**Backend**:
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm run dev
```

## 📖 How to Use

1. Open your browser and navigate to `http://localhost:5173`.
2. Select the type of automation you want to run (e.g., ARC, V-Trans, HMC).
3. Upload the Master CSV file containing the invoice details.
4. Upload all associated PDF vouchers.
5. Click "Process" and watch the real-time progress.
6. Once complete, download the generated ZIP file containing all the merged and processed PDFs.
