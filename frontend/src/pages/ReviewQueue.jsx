import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import StatusBadge from '../components/StatusBadge';

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

  const getStatusColor = (status) => {
    switch (status) {
      case 'Submitted': return 'bg-blue-100 text-blue-800';
      case 'Under Review': return 'bg-purple-100 text-purple-800';
      case 'Processing Failed': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading && !requests.length) return <div className="p-8 text-center text-gray-500">Loading queue...</div>;
  if (error) return <div className="p-8 text-center text-red-600">Error: {error}</div>;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Review Queue</h2>
        <p className="text-gray-600 mt-1">Requests waiting for your action.</p>
      </div>

      <div className="mb-6 flex flex-wrap gap-4">
        <input 
          type="text" 
          placeholder="Search ID or Merchant..." 
          className="border p-2 rounded-lg flex-1 min-w-[200px] shadow-sm"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        <select 
          className="border p-2 rounded-lg shadow-sm"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="Submitted">Submitted</option>
          <option value="Under Review">Under Review</option>
          <option value="Processing Failed">Processing Failed</option>
        </select>
        <select 
          className="border p-2 rounded-lg shadow-sm"
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
          className="border p-2 rounded-lg shadow-sm"
          value={filterDate}
          onChange={e => setFilterDate(e.target.value)}
        />
        {user.role !== 'Submitter' && (
          <input 
            type="number"
            placeholder="Assignee ID"
            className="border p-2 rounded-lg shadow-sm w-32"
            value={filterAssignee}
            onChange={e => setFilterAssignee(e.target.value)}
          />
        )}
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned Reviewer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type / Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Merchant / Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {requests.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-6 py-12 text-center text-gray-500">
                  Your queue is empty.
                </td>
              </tr>
            ) : (
              requests.map((req) => (
                <tr key={req.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">#{req.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{req.assigned_reviewer_id ? `Reviewer ${req.assigned_reviewer_id}` : '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>{req.type}</div>
                    <div className="text-gray-500 text-xs">{req.category || '-'}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>{req.merchant_name || '-'}</div>
                    <div className="font-medium">{req.expense_amount ? `$${req.expense_amount.toFixed(2)}` : '-'}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{req.expense_date || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={req.status} /></td>

                      
                    
                  
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link to={`/requests/${req.id}`} className="text-blue-600 hover:text-blue-900">
                      Review
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
