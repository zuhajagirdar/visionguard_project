import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import { PlusCircle, ArrowRight } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';

export default function Dashboard() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  useEffect(() => {
    loadData();
  }, [filterStatus]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashData, reqData] = await Promise.all([
        api.getDashboardMetrics(),
        api.getRequests({ status: filterStatus || undefined })
      ]);
      setMetrics(dashData);
      setRequests(reqData);
    } catch (err) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-48 text-gray-500 gap-2">
        <div className="animate-spin rounded-full h-7 w-7 border-2 border-blue-200 border-t-blue-600" />
        <span className="text-xs">Loading dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-5 max-w-lg mx-auto text-center bg-red-50 rounded-xl border border-red-200">
        <h3 className="text-sm font-semibold text-red-800">Error loading dashboard</h3>
        <p className="text-xs text-red-600 mt-1">{error}</p>
        <button
          onClick={loadData}
          className="mt-3 px-3.5 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Compact Header & Action Row */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-gray-900">
            Reimbursement Dashboard
          </h1>
          <p className="text-xs text-gray-500">
            Tracking requests and verification status for {user?.username}
          </p>
        </div>

        {/* Filter & New Request Actions Aligned */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="flex-1 sm:flex-initial sm:w-44 px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-white text-gray-900 shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="Draft">Draft</option>
            <option value="Submitted">Submitted</option>
            <option value="Under Review">Under Review</option>
            <option value="Processing Failed">Processing Failed</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
            <option value="More Information Required">Action Needed</option>
            <option value="Withdrawn">Withdrawn</option>
          </select>

          {user?.role === 'Submitter' && (
            <Link
              to="/requests/new"
              className="inline-flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-medium text-xs px-3 py-1.5 rounded-lg shadow-sm transition-colors shrink-0 whitespace-nowrap min-h-[30px]"
            >
              <PlusCircle size={14} />
              <span>New Request</span>
            </Link>
          )}
        </div>
      </div>

      {/* Compact Statistics Cards */}
      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-2xs">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Pending</span>
            <p className="text-xl sm:text-2xl font-bold text-gray-900 mt-0.5">{metrics.pending_count}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-2xs">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Approved</span>
            <p className="text-xl sm:text-2xl font-bold text-emerald-700 mt-0.5">{metrics.approved_count}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-2xs">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Rejected</span>
            <p className="text-xl sm:text-2xl font-bold text-rose-700 mt-0.5">{metrics.rejected_count}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-2xs">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Action Needed</span>
            <p className="text-xl sm:text-2xl font-bold text-amber-700 mt-0.5">{metrics.correction_required_count}</p>
          </div>
        </div>
      )}

      {/* Requests List */}
      {requests.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500 text-xs sm:text-sm">
          No reimbursement requests found matching this filter.
        </div>
      ) : (
        <>
          {/* Mobile Compact Cards View (< md) */}
          <div className="block md:hidden space-y-2.5">
            {requests.map(req => (
              <div key={req.id} className="bg-white rounded-xl border border-gray-200 p-3.5 shadow-2xs space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold text-gray-500">#{req.id}</span>
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
                    className="inline-flex items-center gap-1 text-xs font-semibold bg-blue-50 hover:bg-blue-100 text-blue-700 px-2.5 py-1 rounded-md border border-blue-200 transition-colors"
                  >
                    <span>View</span>
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
                  <th className="w-32 lg:w-36 px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Type / Cat</th>
                  <th className="w-auto px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Merchant</th>
                  <th className="w-24 px-3 py-2.5 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Date</th>
                  <th className="w-24 px-3 py-2.5 text-right text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Amount</th>
                  <th className="w-36 px-3 py-2.5 text-center text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Status</th>
                  <th className="w-20 px-3 py-2.5 text-right text-[11px] font-semibold text-gray-600 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {requests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-3 py-2.5 font-mono text-gray-500 font-medium whitespace-nowrap">#{req.id}</td>
                    <td className="px-3 py-2.5 text-gray-900 truncate">
                      <span className="font-medium">{req.type}</span>
                      {req.category && <span className="text-gray-500 text-[11px] block truncate">{req.category}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-gray-900">
                      <div className="truncate font-medium" title={req.merchant_name || '-'}>
                        {req.merchant_name || '-'}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-gray-600 whitespace-nowrap text-xs">
                      {req.expense_date || '-'}
                    </td>
                    <td className="px-3 py-2.5 font-medium font-mono text-gray-900 whitespace-nowrap text-right">
                      {req.expense_amount ? `$${req.expense_amount.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-3 py-2.5 text-center whitespace-nowrap">
                      <StatusBadge status={req.status} />
                    </td>
                    <td className="px-3 py-2.5 text-right whitespace-nowrap">
                      <Link
                        to={`/requests/${req.id}`}
                        className="text-xs font-semibold bg-blue-50 hover:bg-blue-100 text-blue-700 px-2.5 py-1 rounded-md border border-blue-200 transition-colors inline-flex items-center gap-1"
                      >
                        <span>View</span>
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
