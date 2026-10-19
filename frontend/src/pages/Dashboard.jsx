import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import { FileText, Clock, CheckCircle, XCircle } from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [metrics, setMetrics] = useState(null);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDate, setFilterDate] = useState('');
  const [filterAssignee, setFilterAssignee] = useState('');

  // Internal state for advanced filtering from missing fields
  const [filterRequestIds, setFilterRequestIds] = useState([]);

  useEffect(() => {
    loadData();
  }, [searchQuery, filterStatus, filterType, filterDate, filterAssignee]);

  const loadData = async () => {
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
      const metricsData = await api.getDashboardMetrics();
      setMetrics(metricsData);
      setRequests(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Draft': return 'bg-gray-100 text-gray-800';
      case 'Submitted': return 'bg-blue-100 text-blue-800';
      case 'Under Review': return 'bg-purple-100 text-purple-800';
      case 'More Information Required': return 'bg-yellow-100 text-yellow-800';
      case 'Approved': return 'bg-green-100 text-green-800';
      case 'Rejected': return 'bg-red-100 text-red-800';
      case 'Processing Failed': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const displayRequests = requests.filter(req => {
    if (filterRequestIds.length > 0) {
      return filterRequestIds.includes(req.id);
    }
    return true;
  });

  if (loading && !requests.length) return <div className="p-8 text-center text-gray-500">Loading dashboard...</div>;
  if (error) return <div className="p-8 text-center text-red-600">Error: {error}</div>;

  return (
    <div className="p-8">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Welcome, {user.username}</h2>
          <p className="text-gray-600 mt-1">Here is the status of your requests.</p>
        </div>
        {user.role === 'Submitter' && (
          <Link to="/requests/new" className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium transition-colors">
            + New Request
          </Link>
        )}
      </div>

      {metrics && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
            <div 
              className="bg-white p-4 rounded-lg shadow border border-gray-200 cursor-pointer hover:border-blue-400"
              onClick={() => { setFilterStatus('Pending'); setSearchQuery(''); setFilterRequestIds([]); }}
            >
              <div className="text-gray-500 text-sm font-medium">Pending</div>
              <div className="text-2xl font-bold text-gray-900">{metrics.pending_count}</div>
            </div>
            <div 
              className="bg-white p-4 rounded-lg shadow border border-gray-200 cursor-pointer hover:border-green-400"
              onClick={() => { setFilterStatus('Approved'); setSearchQuery(''); setFilterRequestIds([]); }}
            >
              <div className="text-gray-500 text-sm font-medium">Approved</div>
              <div className="text-2xl font-bold text-green-600">{metrics.approved_count}</div>
            </div>
            <div 
              className="bg-white p-4 rounded-lg shadow border border-gray-200 cursor-pointer hover:border-red-400"
              onClick={() => { setFilterStatus('Rejected'); setSearchQuery(''); setFilterRequestIds([]); }}
            >
              <div className="text-gray-500 text-sm font-medium">Rejected</div>
              <div className="text-2xl font-bold text-red-600">{metrics.rejected_count}</div>
            </div>
            <div 
              className="bg-white p-4 rounded-lg shadow border border-gray-200 cursor-pointer hover:border-yellow-400"
              onClick={() => { setFilterStatus('More Information Required'); setSearchQuery(''); setFilterRequestIds([]); }}
            >
              <div className="text-gray-500 text-sm font-medium">Action Required</div>
              <div className="text-2xl font-bold text-yellow-600">{metrics.correction_required_count}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
              <div className="text-gray-500 text-sm font-medium">Avg Turnaround</div>
              <div className="text-2xl font-bold text-blue-600">
                {metrics.average_review_turnaround_hours !== null ? 
                  `${metrics.average_review_turnaround_hours.toFixed(1)}h` : 'N/A'}
              </div>
            </div>
          </div>
          
          <div className="mb-8 bg-white p-4 rounded-lg shadow border border-gray-200">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-lg font-medium text-gray-900">Frequent Missing/Unreadable Fields</h3>
              {filterRequestIds.length > 0 && (
                <button 
                  onClick={() => setFilterRequestIds([])}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Clear Selection
                </button>
              )}
            </div>
            {metrics.frequent_missing_fields && metrics.frequent_missing_fields.length > 0 ? (
              <ul className="list-disc pl-5">
                {metrics.frequent_missing_fields.map((f, i) => (
                  <li key={i} className="text-gray-700 mb-1">
                    <span 
                      className="font-semibold cursor-pointer hover:text-blue-600 underline decoration-dotted"
                      onClick={() => {
                        setFilterStatus('');
                        setSearchQuery('');
                        setFilterRequestIds(f.request_ids);
                      }}
                    >
                      {f.field_name}
                    </span>
                    : {f.count} instances
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 text-sm">No missing fields recorded.</p>
            )}
          </div>
        </>
      )}

      <div className="mb-6 flex flex-wrap gap-4">
        <input 
          type="text" 
          placeholder="Search ID or Merchant..." 
          className="border p-2 rounded-lg flex-1 min-w-[200px] shadow-sm"
          value={searchQuery}
          onChange={e => { setSearchQuery(e.target.value); setFilterRequestIds([]); }}
        />
        <select 
          className="border p-2 rounded-lg shadow-sm"
          value={filterStatus}
          onChange={e => { setFilterStatus(e.target.value); setFilterRequestIds([]); }}
        >
          <option value="">All Statuses</option>
          <option value="Draft">Draft</option>
          <option value="Submitted">Submitted</option>
          <option value="Under Review">Under Review</option>
          <option value="More Information Required">More Info Required</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
          <option value="Processing Failed">Processing Failed</option>
        </select>
        <select 
          className="border p-2 rounded-lg shadow-sm"
          value={filterType}
          onChange={e => { setFilterType(e.target.value); setFilterRequestIds([]); }}
        >
          <option value="">All Types</option>
          <option value="Travel">Travel</option>
          <option value="Meals">Meals</option>
          <option value="Supplies">Supplies</option>
          <option value="Other">Other</option>
        </select>
        <input 
          type="date"
          className="border p-2 rounded-lg shadow-sm"
          value={filterDate}
          onChange={e => { setFilterDate(e.target.value); setFilterRequestIds([]); }}
        />
        {user.role !== 'Submitter' && (
          <input 
            type="number"
            placeholder="Assignee ID"
            className="border p-2 rounded-lg shadow-sm w-32"
            value={filterAssignee}
            onChange={e => { setFilterAssignee(e.target.value); setFilterRequestIds([]); }}
          />
        )}
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type / Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Merchant</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned Reviewer</th>
<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {displayRequests.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-6 py-12 text-center text-gray-500">
                  {(searchQuery || filterStatus || filterType || filterDate || filterAssignee || filterRequestIds.length > 0) 
                    ? "No requests found matching your filters." 
                    : (user.role === 'Submitter' ? "No requests found. Create a new draft to get started!" : "No requests available.")}
                </td>
              </tr>
            ) : (
              displayRequests.map((req) => (
                <tr key={req.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">#{req.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>{req.type}</div>
                    <div className="text-gray-500 text-xs">{req.category || '-'}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{req.merchant_name || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{req.expense_date || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {req.expense_amount ? `$${req.expense_amount.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {req.assigned_reviewer_id ? `User ${req.assigned_reviewer_id}` : 'Unassigned'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(req.status)}`}>
                      {req.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link to={`/requests/${req.id}`} className="text-blue-600 hover:text-blue-900">
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
