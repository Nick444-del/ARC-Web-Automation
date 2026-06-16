import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Layers, FileText, ChevronLeft, ChevronRight } from 'lucide-react';

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`bg-white border-r border-gray-200 h-screen transition-all duration-300 flex flex-col ${collapsed ? 'w-20' : 'w-64'}`}>
      <div className="p-4 flex items-center justify-between border-b border-gray-200 h-16">
        {!collapsed && <span className="font-bold text-lg whitespace-nowrap">Invoice Portal</span>}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className={`p-2 rounded-lg hover:bg-gray-100 ${collapsed ? 'mx-auto' : ''}`}
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
        <NavLink 
          to="/" 
          className={({ isActive }) => `flex items-center gap-3 p-3 rounded-xl transition-colors ${isActive ? 'bg-black text-white shadow-md' : 'text-gray-600 hover:bg-gray-100 hover:text-black'}`}
          title="ARC Invoice Portal"
        >
          <Layers size={24} className="shrink-0" />
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="font-medium whitespace-nowrap">ARC Invoices</span>
            </div>
          )}
        </NavLink>
        
        <NavLink 
          to="/vtrans" 
          className={({ isActive }) => `flex items-center gap-3 p-3 rounded-xl transition-colors ${isActive ? 'bg-black text-white shadow-md' : 'text-gray-600 hover:bg-gray-100 hover:text-black'}`}
          title="V-Trans Invoice Portal"
        >
          <FileText size={24} className="shrink-0" />
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="font-medium whitespace-nowrap">V-Trans Invoices</span>
            </div>
          )}
        </NavLink>
      </nav>
      
      {!collapsed && (
        <div className="p-4 text-xs text-gray-400 border-t border-gray-100 text-center">
          Automation System
        </div>
      )}
    </div>
  );
}
