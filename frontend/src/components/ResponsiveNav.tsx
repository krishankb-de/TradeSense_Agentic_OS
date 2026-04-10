import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Home, Users, Briefcase, UserCheck, DollarSign } from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigationItems: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Leads', href: '/leads', icon: Users },
  { name: 'Jobs', href: '/jobs', icon: Briefcase },
  { name: 'Technicians', href: '/technicians', icon: UserCheck },
  { name: 'Cost Optimization', href: '/cost-optimization', icon: DollarSign },
];

/**
 * ResponsiveNav component with mobile-first design
 * - Desktop: Horizontal navigation with icons and text
 * - Mobile: Hamburger menu with slide-in drawer
 * - Active navigation highlighting
 * - Smooth hover transitions
 * 
 * Validates: Requirements 8.1, 10.1, 10.2, 10.3, 10.4, 10.5
 */
export function ResponsiveNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <>
      {/* Desktop Navigation - Hidden on mobile */}
      <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`inline-flex items-center px-1 pt-1 border-b-2 font-medium transition-all ${
                isActive
                  ? 'text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
              style={{
                fontSize: 'var(--text-sm)',
                borderBottomColor: isActive ? 'var(--color-primary-500)' : undefined,
                transitionDuration: 'var(--transition-base)',
              }}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className="w-4 h-4 mr-2" aria-hidden="true" />
              {item.name}
            </Link>
          );
        })}
      </div>

      {/* Mobile Menu Button - Hidden on desktop */}
      <button
        type="button"
        className="sm:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset transition-colors"
        style={{
          borderRadius: 'var(--radius-md)',
          transitionDuration: 'var(--transition-base)',
          minWidth: '44px',
          minHeight: '44px',
        }}
        onClick={() => setMobileMenuOpen(true)}
        aria-expanded={mobileMenuOpen}
        aria-label="Open navigation menu"
      >
        <Menu className="h-6 w-6" aria-hidden="true" />
      </button>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-75 z-40 sm:hidden"
          onClick={closeMobileMenu}
          aria-hidden="true"
        />
      )}

      {/* Mobile Menu Drawer - Slide in from right */}
      <div
        className={`fixed inset-y-0 right-0 max-w-xs w-full bg-white z-50 transform transition-transform ease-in-out sm:hidden ${
          mobileMenuOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{
          boxShadow: 'var(--shadow-xl)',
          transitionDuration: 'var(--transition-slow)',
          zIndex: 'var(--z-dropdown)',
        }}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation menu"
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900" style={{ fontSize: 'var(--text-lg)' }}>
            Navigation
          </h2>
          <button
            type="button"
            className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset transition-colors"
            style={{
              borderRadius: 'var(--radius-md)',
              transitionDuration: 'var(--transition-base)',
              minWidth: '44px',
              minHeight: '44px',
            }}
            onClick={closeMobileMenu}
            aria-label="Close navigation menu"
          >
            <X className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
        <nav className="flex flex-col p-4 space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={closeMobileMenu}
                className={`flex items-center px-4 py-3 font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-blue-700 border-l-4'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
                style={{
                  fontSize: 'var(--text-base)',
                  backgroundColor: isActive ? 'var(--color-primary-50)' : undefined,
                  borderLeftColor: isActive ? 'var(--color-primary-500)' : undefined,
                  borderRadius: 'var(--radius-md)',
                  transitionDuration: 'var(--transition-base)',
                  minHeight: '44px',
                }}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="w-5 h-5 mr-3" aria-hidden="true" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}
