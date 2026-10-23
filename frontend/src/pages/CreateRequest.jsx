import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';

export default function CreateRequest() {
  const [type, setType] = useState('Travel');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const newReq = await api.createRequest({ type });
      navigate(`/requests/${newReq.id}`);
    } catch (err) {
      setError(err.message || 'Failed to create request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-gray-900">Create New Request</h2>
        <p className="text-xs sm:text-sm text-gray-500 mt-0.5">Start a new expense reimbursement request draft.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200 space-y-5">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-xs font-medium">
            {error}
          </div>
        )}
        
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
            Expense Type
          </label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="block w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm bg-white text-gray-900 shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="Travel">Travel</option>
            <option value="Meals">Meals</option>
            <option value="Supplies">Supplies</option>
            <option value="Other">Other</option>
          </select>
        </div>

        <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-3 border-t border-gray-100">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="w-full sm:w-auto px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none cursor-pointer min-h-[40px]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="w-full sm:w-auto px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-blue-300 cursor-pointer min-h-[40px] transition-colors"
          >
            {loading ? 'Creating...' : 'Create Draft'}
          </button>
        </div>
      </form>
    </div>
  );
}
