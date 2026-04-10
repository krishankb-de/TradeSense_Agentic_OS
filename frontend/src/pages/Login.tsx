import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { FormField } from '../components/FormField';
import { formValidator } from '../services/formValidator';
import { errorHandler } from '../services/errorHandler';
import { ValidationResult } from '../services/types';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailValidation, setEmailValidation] = useState<ValidationResult | undefined>();
  const [passwordValidation, setPasswordValidation] = useState<ValidationResult | undefined>();
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleEmailBlur = () => {
    setEmailValidation(formValidator.validateEmail(email));
  };

  const handlePasswordBlur = () => {
    setPasswordValidation(formValidator.validatePassword(password));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate all fields before submission
    const emailResult = formValidator.validateEmail(email);
    const passwordResult = formValidator.validatePassword(password);

    setEmailValidation(emailResult);
    setPasswordValidation(passwordResult);

    // Don't submit if validation fails
    if (!emailResult.isValid || !passwordResult.isValid) {
      return;
    }

    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      errorHandler.handleError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8"
      style={{ backgroundColor: 'var(--color-gray-50)' }}
    >
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 
            className="mt-6 text-center font-extrabold text-gray-900"
            style={{ fontSize: 'var(--text-3xl)' }}
          >
            TradeSense
          </h2>
          <p 
            className="mt-2 text-center text-gray-600"
            style={{ fontSize: 'var(--text-sm)' }}
          >
            Sign in to your account
          </p>
        </div>
        <form 
          className="mt-8 space-y-6" 
          onSubmit={handleSubmit}
          aria-label="Login form"
        >
          <FormField
            label="Email address"
            name="email"
            type="email"
            value={email}
            onChange={setEmail}
            onBlur={handleEmailBlur}
            validation={emailValidation}
            required
            disabled={loading}
          />

          <FormField
            label="Password"
            name="password"
            type="password"
            value={password}
            onChange={setPassword}
            onBlur={handlePasswordBlur}
            validation={passwordValidation}
            required
            disabled={loading}
          />

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent font-medium rounded-md text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              style={{
                backgroundColor: 'var(--color-primary-600)',
                fontSize: 'var(--text-sm)',
                borderRadius: 'var(--radius-md)',
                transitionDuration: 'var(--transition-base)',
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary-700)';
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary-600)';
                }
              }}
              data-testid="login-submit-button"
              aria-label={loading ? 'Signing in, please wait' : 'Sign in to your account'}
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />}
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
