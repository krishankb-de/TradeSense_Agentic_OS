import { Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import UserProfile from './UserProfile';
import { ResponsiveNav } from './ResponsiveNav';

export default function Layout() {
  const { logout, user, isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-gray-100)' }}>
      {/* Skip to main content link for keyboard navigation */}
      <a href="#main-content" className="skip-to-main">
        Skip to main content
      </a>
      
      <nav 
        className="bg-white" 
        style={{ boxShadow: 'var(--shadow-sm)' }}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 
                  className="font-bold" 
                  style={{ 
                    fontSize: 'var(--text-xl)', 
                    color: 'var(--color-primary-600)' 
                  }}
                  role="banner"
                >
                  TradeSense
                </h1>
              </div>
              <ResponsiveNav />
            </div>
            <div className="flex items-center">
              {isAuthenticated && user && (
                <UserProfile
                  user={{
                    email: user.email,
                    role: user.role || 'User',
                    name: user.name,
                    avatar: user.avatar,
                  }}
                  onLogout={logout}
                />
              )}
            </div>
          </div>
        </div>
      </nav>
      <main 
        id="main-content"
        className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8"
        role="main"
        aria-label="Main content"
      >
        <Outlet />
      </main>
    </div>
  );
}
