import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Layers, FileText, ChevronLeft, ChevronRight, Moon, Sun } from 'lucide-react';

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  return (
    <div className={`bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 h-screen transition-all duration-300 flex flex-col ${collapsed ? 'w-20' : 'w-64'}`}>
      <div className="p-4 flex items-center justify-between border-b border-gray-200 dark:border-gray-800 h-16 text-black dark:text-white">
        {!collapsed && <span className="font-bold text-lg whitespace-nowrap">Invoice Portal</span>}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className={`p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 ${collapsed ? 'mx-auto' : ''}`}
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
        <NavLink 
          to="/" 
          className={({ isActive }) => `flex items-center gap-3 p-3 rounded-xl transition-colors ${isActive ? 'bg-black dark:bg-white text-white dark:text-black shadow-md' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-black dark:hover:text-white'}`}
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
          className={({ isActive }) => `flex items-center gap-3 p-3 rounded-xl transition-colors ${isActive ? 'bg-black dark:bg-white text-white dark:text-black shadow-md' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-black dark:hover:text-white'}`}
          title="V-Trans Invoice Portal"
        >
          <FileText size={24} className="shrink-0" />
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="font-medium whitespace-nowrap">V-Trans Invoices</span>
            </div>
          )}
        </NavLink>
        
        <NavLink 
          to="/hmc" 
          className={({ isActive }) => `flex items-center gap-3 p-3 rounded-xl transition-colors ${isActive ? 'bg-black dark:bg-white text-white dark:text-black shadow-md' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-black dark:hover:text-white'}`}
          title="HMC Invoice Portal"
        >
          <Layers size={24} className="shrink-0" />
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="font-medium whitespace-nowrap">HMC Invoices</span>
            </div>
          )}
        </NavLink>
      </nav>
      
      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <button
          onClick={() => setIsDark(!isDark)}
          className={`flex items-center gap-3 p-3 w-full rounded-xl transition-colors text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-black dark:hover:text-white ${collapsed ? 'justify-center' : ''}`}
          title="Toggle Dark Mode"
        >
          {isDark ? <Sun size={24} className="shrink-0" /> : <Moon size={24} className="shrink-0" />}
          {!collapsed && (
            <span className="font-medium whitespace-nowrap">
              {isDark ? 'Light Mode' : 'Dark Mode'}
            </span>
          )}
        </button>
      </div>

      {!collapsed && (
        <div className="p-4 text-xs text-gray-400 dark:text-gray-500 border-t border-gray-100 dark:border-gray-800 text-center">
          Automation System
        </div>
      )}
    </div>
  );
}
