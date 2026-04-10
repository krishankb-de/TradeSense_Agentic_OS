import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UserProfile from '../components/UserProfile';

describe('UserProfile Component', () => {
  const mockUser = {
    email: 'test@example.com',
    role: 'Admin',
    name: 'Test User',
  };

  const mockOnLogout = vi.fn();

  it('should display user email', () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('should display user role badge', () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('should display avatar with initials when no avatar image provided', () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    // Should display initials "TU" from "Test User"
    expect(screen.getByText('TU')).toBeInTheDocument();
  });

  it('should display avatar image when provided', () => {
    const userWithAvatar = {
      ...mockUser,
      avatar: 'https://example.com/avatar.jpg',
    };
    
    render(<UserProfile user={userWithAvatar} onLogout={mockOnLogout} />);
    
    const avatarImg = screen.getByAltText('Test User');
    expect(avatarImg).toBeInTheDocument();
    expect(avatarImg).toHaveAttribute('src', 'https://example.com/avatar.jpg');
  });

  it('should show dropdown menu on click', async () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    const profileButton = screen.getByRole('button', { name: /user profile menu/i });
    fireEvent.click(profileButton);
    
    await waitFor(() => {
      expect(screen.getByRole('menu')).toBeInTheDocument();
    });
  });

  it('should display logout option in dropdown with danger styling', async () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    const profileButton = screen.getByRole('button', { name: /user profile menu/i });
    fireEvent.click(profileButton);
    
    await waitFor(() => {
      const logoutButton = screen.getByRole('menuitem', { name: /logout/i });
      expect(logoutButton).toBeInTheDocument();
      expect(logoutButton).toHaveClass('text-red-700');
    });
  });

  it('should call onLogout when logout option is clicked', async () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    const profileButton = screen.getByRole('button', { name: /user profile menu/i });
    fireEvent.click(profileButton);
    
    await waitFor(() => {
      const logoutButton = screen.getByRole('menuitem', { name: /logout/i });
      fireEvent.click(logoutButton);
    });
    
    expect(mockOnLogout).toHaveBeenCalledTimes(1);
  });

  it('should close dropdown when clicking outside', async () => {
    render(
      <div>
        <UserProfile user={mockUser} onLogout={mockOnLogout} />
        <div data-testid="outside">Outside element</div>
      </div>
    );
    
    const profileButton = screen.getByRole('button', { name: /user profile menu/i });
    fireEvent.click(profileButton);
    
    await waitFor(() => {
      expect(screen.getByRole('menu')).toBeInTheDocument();
    });
    
    // Click outside
    const outsideElement = screen.getByTestId('outside');
    fireEvent.mouseDown(outsideElement);
    
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  it('should display profile settings and help options in dropdown', async () => {
    render(<UserProfile user={mockUser} onLogout={mockOnLogout} />);
    
    const profileButton = screen.getByRole('button', { name: /user profile menu/i });
    fireEvent.click(profileButton);
    
    await waitFor(() => {
      expect(screen.getByRole('menuitem', { name: /profile settings/i })).toBeInTheDocument();
      expect(screen.getByRole('menuitem', { name: /help & support/i })).toBeInTheDocument();
    });
  });

  it('should use email initials when name is not provided', () => {
    const userWithoutName = {
      email: 'john.doe@example.com',
      role: 'User',
    };
    
    render(<UserProfile user={userWithoutName} onLogout={mockOnLogout} />);
    
    // Should display first 2 characters of email "JO"
    expect(screen.getByText('JO')).toBeInTheDocument();
  });

  it('should apply correct role badge colors', () => {
    const { rerender } = render(
      <UserProfile user={{ ...mockUser, role: 'Admin' }} onLogout={mockOnLogout} />
    );
    
    let roleBadge = screen.getByText('Admin');
    expect(roleBadge).toHaveClass('bg-purple-100', 'text-purple-800');
    
    rerender(<UserProfile user={{ ...mockUser, role: 'Technician' }} onLogout={mockOnLogout} />);
    roleBadge = screen.getByText('Technician');
    expect(roleBadge).toHaveClass('bg-blue-100', 'text-blue-800');
    
    rerender(<UserProfile user={{ ...mockUser, role: 'User' }} onLogout={mockOnLogout} />);
    roleBadge = screen.getByText('User');
    expect(roleBadge).toHaveClass('bg-gray-100', 'text-gray-800');
  });
});
