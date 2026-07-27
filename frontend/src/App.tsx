import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Login from './pages/Login';
import Register from './pages/Register';
import Video from './pages/Video';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './layouts/Dashboard';

function App() {
  return (
    <Router>
      <Routes>
        {/* Dashboard layout is nested parent routing shell, protected by login check */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } 
        >
          {/* Default page content rendered inside Dashboard's <Outlet /> */}
          <Route index element={<Video />} />
          {/* Expandable: target settings, analytics, etc. as child paths */}
        </Route>
        
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
