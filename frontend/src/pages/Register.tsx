import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, Lock, UserPlus, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const Register: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  
  const { register, loading, error, success, setError, getCurrentUser } = useAuth();
  const navigate = useNavigate();

  // If already logged in, redirect to main page
  useEffect(() => {
    if (getCurrentUser()) {
      navigate('/');
    }
  }, [navigate, getCurrentUser]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setError(null);

    if (!username.trim() || !password.trim() || !confirmPassword.trim()) {
      setValidationError('Please fill in all fields.');
      return;
    }

    if (password !== confirmPassword) {
      setValidationError('Passwords do not match.');
      return;
    }

    if (password.length < 4) {
      setValidationError('Password must be at least 4 characters long.');
      return;
    }

    try {
      await register({ username, password });
      // Redirect after 2 seconds on success
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch {
      // Error handled by useAuth
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">Create Account</h2>
        <p className="auth-subtitle">Register to explore search features</p>

        {success && (
          <div className="alert alert-success">
            <CheckCircle className="alert-icon" size={18} />
            <span>{success}</span>
          </div>
        )}

        {(error || validationError) && (
          <div className="alert alert-error">
            <AlertCircle className="alert-icon" size={18} />
            <span>{validationError || error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">
              Username
            </label>
            <div className="form-input-wrapper">
              <User className="form-input-icon" size={18} />
              <input
                id="username"
                type="text"
                className="form-input"
                placeholder="Choose a username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading || !!success}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Password
            </label>
            <div className="form-input-wrapper">
              <Lock className="form-input-icon" size={18} />
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading || !!success}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirm-password">
              Confirm Password
            </label>
            <div className="form-input-wrapper">
              <Lock className="form-input-icon" size={18} />
              <input
                id="confirm-password"
                type="password"
                className="form-input"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading || !!success}
              />
            </div>
          </div>

          <button type="submit" className="auth-button" disabled={loading || !!success}>
            {loading ? (
              <span className="spinner"></span>
            ) : (
              <>
                <UserPlus size={18} />
                <span>Sign Up</span>
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account? 
          <Link to="/login" className="auth-link">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
};
export default Register;
