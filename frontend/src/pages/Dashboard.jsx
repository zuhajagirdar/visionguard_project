import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import { PlusCircle } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';

export default function Dashboard() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters – keep simple status filter for now
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
      <div className="flex justify-center items-center h-64 text-gray-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center bg-red-50 rounded-lg border border-red-200">
        <h3 className="text-lg font-semibold text-red-800">Error loading dashboard</h3>
        <p className="text-red-600 mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* Greeting */}
      <h2 className="text-2xl font-bold text-gray-900">Welcome, {user?.username}</h2>

      {/* Metrics cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card bg-surface">
            <p className="text-sm text-gray-500">Pending</p>
            <p className="text-2xl font-bold text-gray-800">{metrics.pending_count}</p>
          </div>
          <div className="card bg-surface">
            <p className="text-sm text-gray-500">Approved</p>
            <p className="text-2xl font-bold text-gray-800">{metrics.approved_count}</p>
          </div>
          <div className="card bg-surface">
            <p className="text-sm text-gray-500">Rejected</p>
            <p className="text-2xl font-bold text-gray-800">{metrics.rejected_count}</p>
          </div>
          <div className="card bg-surface">
            <p className="text-sm text-gray-500">More Info Required</p>
            <p className="text-2xl font-bold text-gray-800">{metrics.correction_required_count}</p>
          </div>
        </div>
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-4">
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="border p-2 rounded focus:outline-none focus:ring-primary focus:border-primary"
        >
          <option value="">All Statuses</option>
          <option value="Draft">Draft</option>
          <option value="Submitted">Submitted</option>
          <option value="Under Review">Under Review</option>
          <option value="Processing Failed">Processing Failed</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
          <option value="More Information Required">More Info Required</option>
          <option value="Withdrawn">Withdrawn</option>
        </select>
        {user?.role === 'Submitter' && (
          <Link
            to="/requests/new"
            className="btn-primary flex items-center gap-2"
          >
            <PlusCircle size={18} /> New Request
          </Link>
        )}
      </div>

      {/* Requests table */}
      <div className="overflow-x-auto bg-white rounded-xl shadow-sm border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type / Category</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Merchant</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {requests.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  No requests found.
                </td>
              </tr>
            ) : (
              requests.map(req => (
                <tr key={req.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm text-gray-900">#{req.id}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">
                    <div>{req.type}</div>
                    {req.category && <div className="text-gray-500 text-xs">{req.category}</div>}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900">{req.merchant_name || '-'}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">{req.expense_date || '-'}</td>
                  <td className="px-4 py-2 text-sm font-medium text-gray-900">
                    {req.expense_amount ? `$${req.expense_amount.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={req.status} />
                  </td>
                  <td className="px-4 py-2 text-right text-sm font-medium">
                    <Link
                      to={`/requests/${req.id}`}
                      className="text-primary hover:underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
