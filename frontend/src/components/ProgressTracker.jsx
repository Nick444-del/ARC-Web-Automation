import { useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';

export function ProgressTracker({ logs, status }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="bg-black rounded-xl p-4 h-64 flex flex-col font-mono text-sm shadow-inner border border-gray-800">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-800">
        <h3 className="text-gray-300 font-semibold flex items-center gap-2">
          {status === 'processing' && <Loader2 className="h-4 w-4 animate-spin text-white" />}
          System Console
        </h3>
        <span className="text-xs text-gray-500 uppercase tracking-wider">{status}</span>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
        {logs.length === 0 ? (
          <p className="text-gray-600 italic">Awaiting instructions...</p>
        ) : (
          logs.map((log, i) => {
            let colorClass = "text-gray-300";
            if (log.includes("✅")) colorClass = "text-white";
            if (log.includes("❌")) colorClass = "text-gray-500";
            if (log.includes("⚠️")) colorClass = "text-gray-400";
            
            return (
              <div key={i} className={`flex items-start gap-2 ${colorClass}`}>
                <span className="text-gray-600 select-none">{`>`}</span>
                <span className="break-all">{log}</span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
