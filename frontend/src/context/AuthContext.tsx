import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

interface AuthContextType {
  isAuthenticated: boolean;
  user: {
    email: string;
    role?: string;
    name?: string;
    avatar?: string;
  } | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  token: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      // Decode token to extract user information
      try {
        const tokenPayload = JSON.parse(atob(storedToken.split('.')[1]));
        const userEmail = tokenPayload.sub || tokenPayload.email || 'user@example.com';
        const userRole = tokenPayload.role || tokenPayload.user_role || 'User';
        
        setToken(storedToken);
        setUser({
          email: userEmail,
          role: userRole,
        });
        setIsAuthenticated(true);
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
      } catch (e) {
        console.warn('Failed to decode stored token:', e);
        // Clear invalid token
        localStorage.removeItem('token');
      }
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // OAuth2PasswordRequestForm expects form data with 'username' and 'password' fields
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      const response = await axios.post('/api/v1/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      
      const { access_token } = response.data;
      
      // Decode JWT token to extract user information
      let userRole = 'User';
      try {
        const tokenPayload = JSON.parse(atob(access_token.split('.')[1]));
        userRole = tokenPayload.role || tokenPayload.user_role || 'User';
      } catch (e) {
        console.warn('Failed to decode token:', e);
      }
      
      setToken(access_token);
      setUser({ 
        email,
        role: userRole,
      });
      setIsAuthenticated(true);
      localStorage.setItem('token', access_token);
      
      // Set axios default header for subsequent requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
