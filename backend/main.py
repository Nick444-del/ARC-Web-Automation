from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import tempfile
import asyncio
import json
import shutil
from automation import process_automation
from vtrans_automation import process_vtrans_automation

app = FastAPI()

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLANT_DATA_PATH = os.path.join(BASE_DIR, "plant_data.csv")

# In-memory store to map session_id to file paths
sessions = {}

@app.post("/upload")
async def upload_files(
    csv_file: UploadFile = File(...),
    vouchers: list[UploadFile] = File(...),
    include_unmerged: str = Form("false")
):
    session_id = str(uuid.uuid4())
    temp_dir = os.path.join(tempfile.gettempdir(), f"arc_upload_{session_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    vouchers_dir = os.path.join(temp_dir, "vouchers")
    os.makedirs(vouchers_dir, exist_ok=True)
    
    # Save CSV
    csv_path = os.path.join(temp_dir, csv_file.filename)
    with open(csv_path, "wb") as f:
        f.write(await csv_file.read())
        
    # Save Vouchers
    for voucher in vouchers:
        v_path = os.path.join(vouchers_dir, voucher.filename)
        with open(v_path, "wb") as f:
            f.write(await voucher.read())
            
    sessions[session_id] = {
        "csv_path": csv_path,
        "vouchers_dir": vouchers_dir,
        "zip_path": None,
        "include_unmerged": include_unmerged
    }
    
    return {"session_id": session_id}

@app.websocket("/ws/progress/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in sessions:
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid session ID"}))
        await websocket.close()
        return
        
    session_data = sessions[session_id]
    
    try:
        include_unmerged_bool = session_data.get("include_unmerged", "false").lower() == "true"
        # Run automation generator
        generator = process_automation(
            master_csv_path=session_data["csv_path"],
            plant_csv_path=PLANT_DATA_PATH,
            vouchers_dir=session_data["vouchers_dir"],
            base_dir=BASE_DIR,
            session_id=session_id,
            include_unmerged=include_unmerged_bool
        )
        
        for msg in generator:
            if isinstance(msg, dict) and "zip_path" in msg:
                session_data["zip_path"] = msg["zip_path"]
                await websocket.send_text(json.dumps({"type": "complete", "download_url": f"/download/{session_id}"}))
            else:
                await websocket.send_text(json.dumps({"type": "progress", "message": str(msg)}))
                await asyncio.sleep(0.01) # Small delay to yield loop
                
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
    finally:
        await websocket.close()

@app.websocket("/ws/vtrans-progress/{session_id}")
async def vtrans_websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in sessions:
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid session ID"}))
        await websocket.close()
        return
        
    session_data = sessions[session_id]
    
    try:
        include_unmerged_bool = session_data.get("include_unmerged", "false").lower() == "true"
        generator = process_vtrans_automation(
            master_csv_path=session_data["csv_path"],
            plant_csv_path=PLANT_DATA_PATH,
            vouchers_dir=session_data["vouchers_dir"],
            base_dir=BASE_DIR,
            session_id=session_id,
            include_unmerged=include_unmerged_bool
        )
        
        for msg in generator:
            if isinstance(msg, dict) and "zip_path" in msg:
                session_data["zip_path"] = msg["zip_path"]
                await websocket.send_text(json.dumps({"type": "complete", "download_url": f"/download/{session_id}"}))
            else:
                await websocket.send_text(json.dumps({"type": "progress", "message": str(msg)}))
                await asyncio.sleep(0.01)
                
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
    finally:
        await websocket.close()

@app.get("/download/{session_id}")
async def download_zip(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions or not sessions[session_id].get("zip_path"):
        return {"error": "File not found"}
        
    zip_path = sessions[session_id]["zip_path"]
    
    def cleanup():
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            upload_dir = os.path.join(tempfile.gettempdir(), f"arc_upload_{session_id}")
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
            work_dir = os.path.join(tempfile.gettempdir(), f"arc_{session_id}")
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)
            vtrans_work_dir = os.path.join(tempfile.gettempdir(), f"vtrans_{session_id}")
            if os.path.exists(vtrans_work_dir):
                shutil.rmtree(vtrans_work_dir)
            if session_id in sessions:
                del sessions[session_id]
        except Exception as e:
            print(f"Cleanup error: {e}")
            
    background_tasks.add_task(cleanup)
    
    return FileResponse(
        path=zip_path, 
        filename="Completed_Invoices.zip", 
        media_type="application/zip"
    )
