import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { LogOut, LayoutDashboard, PlusCircle, Inbox, Menu, X } from 'lucide-react';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const NavItem = ({ to, icon: Icon, children }) => {
    const isActive = location.pathname === to;
    return (
      <Link
        to={to}
        onClick={() => setMobileMenuOpen(false)}
        className={`flex items-center gap-2.5 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
          isActive
            ? 'bg-blue-50 text-blue-700 shadow-2xs font-semibold'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
        }`}
      >
        <Icon size={18} />
        <span>{children}</span>
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-[#f3f4f6] flex flex-col md:flex-row">
      {/* Mobile Top Header (screens < md) */}
      <header className="md:hidden bg-white border-b border-gray-200 sticky top-0 z-30 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link to="/" className="text-base font-bold tracking-tight text-gray-900">
            Veriflow
          </Link>
          {user?.role && (
            <span className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200 font-medium">
              {user.role}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-100 active:bg-gray-200 cursor-pointer"
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </header>

      {/* Mobile Navigation Dropdown Drawer (< md) */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-gray-200 shadow-sm px-4 py-3 space-y-3 z-20">
          <div className="pb-2 border-b border-gray-100 text-xs text-gray-500">
            User: <span className="font-semibold text-gray-900">{user?.username}</span> • <span className="text-blue-700 font-medium">{user?.role}</span>
          </div>
          <nav className="space-y-1">
            <NavItem to="/" icon={LayoutDashboard}>Dashboard</NavItem>
            {user?.role === 'Submitter' && (
              <NavItem to="/requests/new" icon={PlusCircle}>New Request</NavItem>
            )}
            {(user?.role === 'Reviewer' || user?.role === 'Approver') && (
              <NavItem to="/review-queue" icon={Inbox}>Review Queue</NavItem>
            )}
          </nav>
          <div className="pt-2 border-t border-gray-100">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                handleLogout();
              }}
              className="flex items-center gap-2 text-gray-600 hover:text-red-600 hover:bg-red-50 w-full px-3.5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-colors cursor-pointer"
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}

      {/* Desktop Sticky Sidebar (screens >= md) */}
      <aside className="hidden md:flex w-56 lg:w-60 bg-white border-r border-gray-200 flex-col shrink-0 sticky top-0 h-screen z-20">
        {/* Brand & User Info */}
        <div className="p-4 border-b border-gray-200">
          <Link to="/" className="text-lg font-bold tracking-tight text-gray-900 block">
            Veriflow
          </Link>
          <div className="mt-1 text-xs text-gray-500 truncate" title={`${user?.username} (${user?.role})`}>
            <span className="font-semibold text-gray-900">{user?.username}</span>
            <span className="text-gray-400"> • </span>
            <span className="text-blue-700 font-medium">{user?.role}</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          <NavItem to="/" icon={LayoutDashboard}>Dashboard</NavItem>
          {user?.role === 'Submitter' && (
            <NavItem to="/requests/new" icon={PlusCircle}>New Request</NavItem>
          )}
          {(user?.role === 'Reviewer' || user?.role === 'Approver') && (
            <NavItem to="/review-queue" icon={Inbox}>Review Queue</NavItem>
          )}
        </nav>

        {/* Logout pinned at bottom of viewport-height sidebar via mt-auto */}
        <div className="mt-auto p-3 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-gray-600 hover:text-red-600 w-full px-3.5 py-2 rounded-lg hover:bg-red-50 transition-colors text-xs font-semibold cursor-pointer"
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 p-4 sm:p-5 lg:p-6">
        {children}
      </main>
    </div>
  );
}
