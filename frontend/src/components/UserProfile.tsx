import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Settings, HelpCircle, LogOut } from 'lucide-react';

interface UserProfileProps {
  user: {
    email: string;
    role?: string;
    name?: string;
    avatar?: string;
  };
  onLogout: () => void;
}

interface ProfileMenuItem {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  variant?: 'default' | 'danger';
}

export default function UserProfile({ user, onLogout }: UserProfileProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get user initials for avatar
  const getInitials = (email: string, name?: string): string => {
    if (name) {
      const parts = name.split(' ');
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  };

  // Get role badge color
  const getRoleBadgeColor = (role?: string): string => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return 'bg-purple-100 text-purple-800';
      case 'technician':
        return 'bg-blue-100 text-blue-800';
      case 'user':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isDropdownOpen) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isDropdownOpen]);

  const menuItems: ProfileMenuItem[] = [
    {
      label: 'Profile Settings',
      icon: Settings,
      onClick: () => {
        console.log('Profile settings clicked');
        setIsDropdownOpen(false);
      },
      variant: 'default',
    },
    {
      label: 'Help & Support',
      icon: HelpCircle,
      onClick: () => {
        console.log('Help & Support clicked');
        setIsDropdownOpen(false);
      },
      variant: 'default',
    },
    {
      label: 'Logout',
      icon: LogOut,
      onClick: () => {
        setIsDropdownOpen(false);
        onLogout();
      },
      variant: 'danger',
    },
  ];

  return (
    <div className="relative" ref={dropdownRef} data-testid="user-profile">
      {/* Profile Button */}
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        style={{
          borderRadius: 'var(--radius-lg)',
          transitionDuration: 'var(--transition-base)',
        }}
        aria-label="User profile menu"
        aria-expanded={isDropdownOpen}
        aria-haspopup="true"
      >
        {/* Avatar */}
        <div className="flex-shrink-0">
          {user.avatar ? (
            <img
              src={user.avatar}
              alt={user.name || user.email}
              className="w-10 h-10 rounded-full object-cover"
              style={{ borderRadius: 'var(--radius-full)' }}
            />
          ) : (
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
              style={{
                backgroundColor: 'var(--color-primary-600)',
                fontSize: 'var(--text-sm)',
                borderRadius: 'var(--radius-full)',
              }}
            >
              {getInitials(user.email, user.name)}
            </div>
          )}
        </div>

        {/* User Info */}
        <div className="hidden md:block text-left">
          <div className="font-medium text-gray-900" style={{ fontSize: 'var(--text-sm)' }}>
            {user.email}
          </div>
          {user.role && (
            <div className="flex items-center mt-1">
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded font-medium ${getRoleBadgeColor(
                  user.role
                )}`}
                style={{
                  fontSize: 'var(--text-xs)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                {user.role}
              </span>
            </div>
          )}
        </div>

        {/* Dropdown Icon */}
        <ChevronDown
          className={`w-4 h-4 text-gray-500 transition-transform ${
            isDropdownOpen ? 'transform rotate-180' : ''
          }`}
          style={{ transitionDuration: 'var(--transition-base)' }}
        />
      </button>

      {/* Dropdown Menu */}
      {isDropdownOpen && (
        <div
          className="absolute right-0 mt-2 w-56 rounded-md bg-white ring-1 ring-black ring-opacity-5"
          style={{
            boxShadow: 'var(--shadow-lg)',
            borderRadius: 'var(--radius-md)',
            zIndex: 'var(--z-dropdown)',
          }}
          role="menu"
          aria-orientation="vertical"
          aria-labelledby="user-menu"
        >
          <div className="py-1">
            {/* Mobile: Show user info in dropdown */}
            <div className="md:hidden px-4 py-3 border-b border-gray-100">
              <div className="font-medium text-gray-900" style={{ fontSize: 'var(--text-sm)' }}>
                {user.email}
              </div>
              {user.role && (
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded font-medium mt-1 ${getRoleBadgeColor(
                    user.role
                  )}`}
                  style={{
                    fontSize: 'var(--text-xs)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  {user.role}
                </span>
              )}
            </div>

            {/* Menu Items */}
            {menuItems.map((item, index) => {
              const Icon = item.icon;
              const isDanger = item.variant === 'danger';

              return (
                <button
                  key={index}
                  onClick={item.onClick}
                  className={`w-full text-left px-4 py-2 flex items-center space-x-3 transition-colors ${
                    isDanger
                      ? 'text-red-700 hover:bg-red-50'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                  style={{
                    fontSize: 'var(--text-sm)',
                    transitionDuration: 'var(--transition-base)',
                  }}
                  role="menuitem"
                >
                  <Icon className={`w-4 h-4 ${isDanger ? 'text-red-600' : 'text-gray-500'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
