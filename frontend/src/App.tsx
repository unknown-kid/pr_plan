import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import Home from './pages/Home';
import Login from './pages/Login';
import PaperDetail from './pages/PaperDetail';
import SearchPage from './pages/SearchPage';
import UserProfile from './pages/UserProfile';
import ModelConfig from './pages/ModelConfig';
import useUserStore from './store/userStore';
import api from './services/api';

const App: React.FC = () => {
  const { darkMode, token, user, setUser, logout } = useUserStore();

  useEffect(() => {
    const fetchUser = async () => {
      if (token && !user) {
        try {
          const res = await api.get('/auth/me');
          setUser(res.data);
        } catch (err) {
          logout();
        }
      }
    };
    fetchUser();
  }, [token, user, setUser, logout]);

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={!token ? <Login /> : <Navigate to="/" />} />
          <Route path="/" element={token ? <Home /> : <Navigate to="/login" />} />
          <Route path="/papers/:id" element={token ? <PaperDetail /> : <Navigate to="/login" />} />
          <Route path="/search" element={token ? <SearchPage /> : <Navigate to="/login" />} />
          <Route path="/profile" element={token ? <UserProfile /> : <Navigate to="/login" />} />
          <Route path="/config" element={token ? <ModelConfig /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
