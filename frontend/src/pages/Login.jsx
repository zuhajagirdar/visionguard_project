import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import { Receipt } from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('Submitter');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Username is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { access_token } = await api.login(username.trim()); // role not needed for backend login
      localStorage.setItem('access_token', access_token);
      login({ username: username.trim(), role });
      navigate('/');
    } catch (err) {
      setError(err.message || 'Failed to login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-surface p-8 rounded-xl shadow-lg border border-gray-100">
        <div className="text-center">
          <Receipt className="mx-auto h-12 w-12 text-primary" />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">Veriflow</h2>
          <p className="mt-2 text-sm text-gray-600">Sign in to access the document verification platform</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-error-50 text-error p-3 rounded-md text-sm">{error}</div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="mt-1 block w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
                placeholder="e.g., alice"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="role" className="block text-sm font-medium text-gray-700">Role</label>
              <select
                id="role"
                name="role"
                className="mt-1 block w-full pl-3 pr-10 py-2 border rounded-md focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="Submitter">Submitter</option>
                <option value="Reviewer">Reviewer</option>
                <option value="Approver">Approver</option>
              </select>
            </div>
          </div>
          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:bg-primary/30"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
