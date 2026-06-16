import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function DropZone({ title, accept, maxFiles, onDrop, files }) {
  const handleDrop = useCallback((acceptedFiles) => {
    onDrop(acceptedFiles);
  }, [onDrop]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept,
    maxFiles
  });

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-black dark:text-white">{title}</h3>
      <div 
        {...getRootProps()} 
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ease-in-out",
          isDragActive ? "border-black dark:border-white bg-gray-100 dark:bg-gray-800" : "border-gray-300 dark:border-gray-700 hover:border-black dark:hover:border-white hover:bg-gray-50 dark:hover:bg-gray-800",
          files.length > 0 && "border-black dark:border-white bg-gray-50 dark:bg-gray-800"
        )}
      >
        <input {...getInputProps()} />
        <UploadCloud className="mx-auto h-10 w-10 text-black dark:text-white mb-4" />
        {isDragActive ? (
          <p className="text-black dark:text-white font-medium">Drop files here...</p>
        ) : (
          <p className="text-gray-600 dark:text-gray-400">Drag & drop files here, or click to select</p>
        )}
      </div>
      
      {files.length > 0 && (
        <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          <p className="font-medium text-black dark:text-white mb-1">Selected ({files.length}):</p>
          <ul className="max-h-24 overflow-y-auto space-y-1">
            {files.slice(0, 5).map(f => (
              <li key={f.name} className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-black dark:text-white" />
                <span className="truncate">{f.name}</span>
              </li>
            ))}
            {files.length > 5 && (
              <li className="text-xs text-gray-400 italic">...and {files.length - 5} more</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
