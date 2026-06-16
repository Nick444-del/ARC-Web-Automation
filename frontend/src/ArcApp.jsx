import { useState, useRef } from 'react';
import axios from 'axios';
import { DropZone } from './components/DropZone';
import { ProgressTracker } from './components/ProgressTracker';
import { FileDown, Play, RefreshCw, Layers } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://arc-web-automation.onrender.com';
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws:https://arc-web-automation.onrender.com';

export function ArcApp() {
  const [csvFile, setCsvFile] = useState([]);
  const [vouchers, setVouchers] = useState([]);
  const [includeUnmerged, setIncludeUnmerged] = useState(false);
  const [status, setStatus] = useState('idle'); 
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const wsRef = useRef(null);

  const handleStart = async () => {
    if (csvFile.length === 0) {
      alert("Please upload the master CSV file.");
      return;
    }
    if (vouchers.length === 0) {
      alert("Please upload at least one supporting PDF voucher.");
      return;
    }

    setStatus('uploading');
    setLogs(["Preparing to upload files..."]);

    const formData = new FormData();
    formData.append('csv_file', csvFile[0]);
    formData.append('include_unmerged', includeUnmerged.toString());
    vouchers.forEach(file => {
      formData.append('vouchers', file);
    });

    try {
      setLogs(prev => [...prev, "Uploading data to server..."]);
      const response = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const { session_id } = response.data;
      setLogs(prev => [...prev, "Upload successful. Connecting to automation engine..."]);
      startWebSocket(session_id);

    } catch (error) {
      console.error(error);
      setStatus('error');
      setLogs(prev => [...prev, `❌ Upload failed: ${error.message}`]);
    }
  };

  const startWebSocket = (sessionId) => {
    setStatus('processing');
    const ws = new WebSocket(`${WS_BASE}/ws/progress/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'progress') {
        setLogs(prev => [...prev, data.message]);
      } else if (data.type === 'complete') {
        setDownloadUrl(`${API_BASE}${data.download_url}`);
        setStatus('complete');
        ws.close();
      } else if (data.type === 'error') {
        setStatus('error');
        setLogs(prev => [...prev, `❌ Server Error: ${data.message}`]);
        ws.close();
      }
    };

    ws.onerror = () => {
      setStatus('error');
      setLogs(prev => [...prev, "❌ WebSocket connection lost."]);
    };
  };

  const reset = () => {
    setCsvFile([]);
    setVouchers([]);
    setStatus('idle');
    setLogs([]);
    setDownloadUrl(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="w-full max-w-5xl mb-8 text-center">
        <div className="inline-flex items-center justify-center p-3 bg-black rounded-full mb-4 shadow-lg">
          <Layers className="h-8 w-8 text-white" />
        </div>
        <h1 className="text-4xl font-extrabold text-black tracking-tight">ARC Automation</h1>
        <p className="mt-3 text-lg text-gray-500">Generate and merge your invoices instantly</p>
      </div>

      {/* Main Content */}
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Column: Uploads */}
        <div className="bg-white rounded-2xl p-6 flex flex-col gap-6 shadow-xl border border-gray-200">
          <DropZone 
            title={
              <div className="flex justify-between items-center">
                <span>1. Master Data (CSV)</span>
                <a href="/sample_master.csv" download className="text-xs text-gray-500 hover:text-black underline font-normal">
                  Download Sample CSV
                </a>
              </div>
            }
            accept={{ 'text/csv': ['.csv'] }} 
            maxFiles={1}
            files={csvFile}
            onDrop={setCsvFile}
          />
          
          <DropZone 
            title="2. Supporting Vouchers (PDFs)" 
            accept={{ 'application/pdf': ['.pdf'] }} 
            maxFiles={0} 
            files={vouchers}
            onDrop={setVouchers}
          />

          <div className="flex items-center gap-3 py-2 px-1">
            <button 
              type="button" 
              onClick={() => setIncludeUnmerged(!includeUnmerged)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${includeUnmerged ? 'bg-black' : 'bg-gray-300'}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${includeUnmerged ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
            <span className="text-sm font-medium text-gray-700 cursor-pointer select-none" onClick={() => setIncludeUnmerged(!includeUnmerged)}>
              Include invoices with missing vouchers
            </span>
          </div>

          <div className="mt-auto pt-4 border-t border-gray-200">
            {status === 'idle' || status === 'error' ? (
              <button 
                onClick={handleStart}
                className="w-full py-4 bg-black hover:bg-gray-800 text-white font-bold rounded-xl shadow-md transition-colors flex justify-center items-center gap-2"
              >
                <Play className="h-5 w-5" />
                Generate & Merge
              </button>
            ) : status === 'complete' ? (
               <div className="flex gap-4">
                 <a 
                   href={downloadUrl}
                   download="Completed_Invoices.zip"
                   className="flex-1 py-4 bg-black hover:bg-gray-800 text-white font-bold rounded-xl shadow-md transition-colors flex justify-center items-center gap-2"
                 >
                   <FileDown className="h-5 w-5" />
                   Download Zip
                 </a>
                 <button 
                   onClick={reset}
                   className="px-6 py-4 bg-gray-200 hover:bg-gray-300 text-black font-bold rounded-xl transition-colors flex justify-center items-center gap-2"
                 >
                   <RefreshCw className="h-5 w-5" />
                 </button>
               </div>
            ) : (
              <button disabled className="w-full py-4 bg-gray-100 text-gray-400 font-bold rounded-xl shadow-sm flex justify-center items-center gap-2 cursor-not-allowed">
                <RefreshCw className="h-5 w-5 animate-spin" />
                {status === 'uploading' ? 'Uploading...' : 'Processing...'}
              </button>
            )}
          </div>
        </div>

        {/* Right Column: Progress */}
        <div className="flex flex-col h-full">
           <ProgressTracker logs={logs} status={status} />
        </div>

      </div>
    </div>
  );
}


