import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CreateRequest from './pages/CreateRequest';
import RequestDetail from './pages/RequestDetail';
import SroieEvaluation from './pages/SroieEvaluation';
import ReviewQueue from './pages/ReviewQueue';

const PrivateRoute = ({ children, allowedRoles }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/" />;
  return <Layout>{children}</Layout>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="/requests/new" element={<PrivateRoute allowedRoles={['Submitter']}><CreateRequest /></PrivateRoute>} />
      <Route path="/requests/:id" element={<PrivateRoute><RequestDetail /></PrivateRoute>} />
      <Route path="/review-queue" element={<PrivateRoute allowedRoles={['Reviewer', 'Approver']}><ReviewQueue /></PrivateRoute>} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}
