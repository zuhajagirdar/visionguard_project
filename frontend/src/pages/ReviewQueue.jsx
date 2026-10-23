import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import StatusBadge from '../components/StatusBadge';
import { Search, ArrowRight } from 'lucide-react';

export default function ReviewQueue() {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDate, setFilterDate] = useState('');
  const [filterAssignee, setFilterAssignee] = useState('');

  useEffect(() => {
    loadRequests();
  }, [searchQuery, filterStatus, filterType, filterDate, filterAssignee]);

  const loadRequests = async () => {
    try {
      const params = {};
      if (searchQuery) {
        if (!isNaN(searchQuery)) params.req_id = searchQuery;
        else params.merchant = searchQuery;
      }
      if (filterStatus) params.status = filterStatus;
      if (filterType) params.type = filterType;
      if (filterDate) params.date = filterDate;
      if (filterAssignee) params.assignee_id = filterAssignee;
      
      const data = await api.getRequests(params);
      
      const filtered = data.filter(req => {
        if (user.role === 'Reviewer') {
          return req.status === 'Submitted' || req.status === 'Under Review' || req.status === 'Processing Failed';
        }
        if (user.role === 'Approver') {
          return req.status === 'Under Review'; 
        }
        return false;
      });
      
      setRequests(filtered);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !requests.length) {
    return (
      <div className="flex flex-col justify-center items-center h-48 text-gray-500 gap-2">
        <div className="animate-spin rounded-full h-7 w-7 border-2 border-blue-200 border-t-blue-600" />
        <span className="text-xs">Loading review queue...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-5 max-w-lg mx-auto text-center bg-red-50 rounded-xl border border-red-200">
        <h3 className="text-sm font-semibold text-red-800">Error loading review queue</h3>
        <p className="text-xs text-red-600 mt-1">{error}</p>
        <button
          onClick={loadRequests}
          className="mt-3 px-3.5 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Page Header */}
      <div className="pb-2 border-b border-gray-200">
        <h1 className="text-lg sm:text-xl font-bold tracking-tight text-gray-900">Review Queue</h1>
        <p className="text-xs text-gray-500">
          Reimbursement claims pending your review and decision
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3 sm:p-3.5 rounded-xl border border-gray-200 shadow-2xs space-y-2.5">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <div className="relative">
            <input 
              type="text" 
              placeholder="Search ID or Merchant..." 
              className="w-full pl-8 pr-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-white text-gray-900 shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <Search size={14} className="absolute left-2.5 top-2 text-gray-400" />
          </div>

          <select 
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-white text-gray-900 shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="Submitted">Submitted</option>
            <option value="Under Review">Under Review</option>
            <option value="Processing Failed">Processing Failed</option>
          </select>

          <select 
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-white text-gray-900 shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="Travel">Travel</option>
            <option value="Meals">Meals</option>
            <option value="Supplies">Supplies</option>
            <option value="Other">Other</option>
          </select>

          <input 
            type="date"
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-white text-gray-900 shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={filterDate}
            onChange={e => setFilterDate(e.target.value)}
          />
        </div>

        {user.role !== 'Submitter' && (
          <div className="pt-2 border-t border-gray-100 flex items-center gap-2">
            <label className="text-[11px] font-medium text-gray-500">Assignee ID:</label>
            <input 
              type="number"
              placeholder="e.g. 3"
              className="px-2 py-1 border border-gray-300 rounded-md text-xs w-20 bg-white text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={filterAssignee}
              onChange={e => setFilterAssignee(e.target.value)}
            />
            {filterAssignee && (
              <button
                type="button"
                onClick={() => setFilterAssignee('')}
                className="text-xs text-gray-500 hover:text-gray-800 cursor-pointer"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Review Queue Results */}
      {requests.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500 text-xs sm:text-sm">
          Your review queue is currently empty.
        </div>
      ) : (
        <>
          {/* Mobile Compact Cards View (< md) */}
          <div className="block md:hidden space-y-2.5">
            {requests.map(req => (
              <div key={req.id} className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-2xs space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-semibold text-gray-500">#{req.id}</span>
                    {req.assigned_reviewer_id && (
                      <span className="text-[10px] bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded border border-purple-200 font-medium">
                        Rev #{req.assigned_reviewer_id}
                      </span>
                    )}
                  </div>
                  <StatusBadge status={req.status} />
                </div>

                <div className="space-y-0.5">
                  <p className="font-semibold text-xs sm:text-sm text-gray-900 break-words" title={req.merchant_name || '-'}>
                    {req.merchant_name || 'Unspecified Merchant'}
                  </p>
                  <div className="flex items-center justify-between text-[11px] text-gray-500">
                    <span className="truncate max-w-[180px]">{req.type} {req.category ? `• ${req.category}` : ''}</span>
                    <span>{req.expense_date || '-'}</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-sm sm:text-base font-bold text-gray-900 font-mono">
                    {req.expense_amount ? `$${req.expense_amount.toFixed(2)}` : '--'}
                  </span>
                  <Link
                    to={`/requests/${req.id}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg shadow-sm transition-colors min-h-[32px]"
                  >
                    <span>Review</span>
                    <ArrowRight size={11} />
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop Table View (>= md) - Completely contained, no horizontal scrolling */}
          <div className="hidden md:block bg-white rounded-xl shadow-2xs border border-gray-200 overflow-hidden">
            <table className="w-full table-fixed divide-y divide-gray-200 text-xs sm:text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-14 px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">ID</th>
                  <th className="w-24 px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Reviewer</th>
                  <th className="w-28 lg:w-32 px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Type / Cat</th>
                  <th className="w-auto px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Merchant / Amount</th>
                  <th className="w-24 px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Date</th>
                  <th className="w-32 lg:w-36 px-3 py-2.5 text-center text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Status</th>
                  <th className="w-20 px-3 py-2.5 text-right text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {requests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-3 py-2.5 font-mono text-gray-500 font-medium whitespace-nowrap">#{req.id}</td>
                    <td className="px-3 py-2.5 text-gray-600 text-xs truncate">
                      {req.assigned_reviewer_id ? `Rev #${req.assigned_reviewer_id}` : '—'}
                    </td>
                    <td className="px-3 py-2.5 text-gray-900 truncate">
                      <span className="font-medium">{req.type}</span>
                      {req.category && <span className="text-gray-500 text-[11px] block truncate">{req.category}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-gray-900">
                      <div className="truncate font-medium" title={req.merchant_name || '-'}>{req.merchant_name || '-'}</div>
                      <div className="font-mono text-xs text-gray-600 font-medium">{req.expense_amount ? `$${req.expense_amount.toFixed(2)}` : '—'}</div>
                    </td>
                    <td className="px-3 py-2.5 text-gray-600 whitespace-nowrap text-xs">{req.expense_date || '—'}</td>
                    <td className="px-3 py-2.5 text-center whitespace-nowrap">
                      <StatusBadge status={req.status} />
                    </td>
                    <td className="px-3 py-2.5 text-right whitespace-nowrap">
                      <Link
                        to={`/requests/${req.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white px-2.5 py-1 rounded-md shadow-2xs transition-colors"
                      >
                        <span>Review</span>
                        <ArrowRight size={11} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
