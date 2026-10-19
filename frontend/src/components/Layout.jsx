import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { LogOut, LayoutDashboard, PlusCircle, Inbox, FileText, Activity } from 'lucide-react';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const NavItem = ({ to, icon: Icon, children }) => {
    const isActive = location.pathname === to;
    return (
      <Link
        to={to}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
          isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
        }`}
      >
        <Icon size={20} />
        {children}
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row">
      <aside className="w-full md:w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800">Expense Auth</h1>
          <p className="text-sm text-gray-500 mt-1">Role: <span className="font-medium text-gray-700">{user?.role}</span></p>
          <p className="text-sm text-gray-500">User: <span className="font-medium text-gray-700">{user?.username}</span></p>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          <NavItem to="/" icon={LayoutDashboard}>Dashboard</NavItem>
          
          {user?.role === 'Submitter' && (
            <NavItem to="/requests/new" icon={PlusCircle}>New Request</NavItem>
          )}
          
          {(user?.role === 'Reviewer' || user?.role === 'Approver') && (
            <NavItem to="/review-queue" icon={Inbox}>Review Queue</NavItem>
          )}
          <NavItem to="/eval" icon={Activity}>SROIE Eval</NavItem>
        </nav>

        <div className="p-4 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-gray-600 hover:text-red-600 w-full px-4 py-2 rounded-lg hover:bg-red-50 transition-colors"
          >
            <LogOut size={20} />
            Logout
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
