import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';
import { authApi, AuthResponse, LoginCredentials, User } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  const queryClient = useQueryClient();

  // Check for existing token on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const refreshToken = localStorage.getItem('refresh_token');

        if (token && refreshToken) {
          // Try to get user profile
          const userData = await authApi.getProfile();
          setUser(userData);
          setIsAuthenticated(true);
        }
      } catch (error) {
        // Token might be expired, try refresh
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          try {
            await handleRefreshToken();
          } catch (refreshError) {
            // Clear invalid tokens
            clearTokens();
          }
        }
      } finally {
        setIsInitialized(true);
      }
    };

    initializeAuth();
  }, []);

  // User profile query
  const { refetch: refetchProfile } = useQuery(
    ['user-profile'],
    authApi.getProfile,
    {
      enabled: false,
      onSuccess: (userData) => {
        setUser(userData);
        setIsAuthenticated(true);
      },
      onError: () => {
        clearTokens();
      },
    }
  );

  // Login mutation
  const loginMutation = useMutation(authApi.login, {
    onSuccess: (response: AuthResponse) => {
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      
      // Set authorization header
      authApi.setAuthToken(response.access_token);
      
      // Fetch user profile
      refetchProfile();
      
      toast.success('Login successful!');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
    },
  });

  // Refresh token mutation
  const refreshTokenMutation = useMutation(authApi.refreshToken, {
    onSuccess: (response: AuthResponse) => {
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      
      // Set authorization header
      authApi.setAuthToken(response.access_token);
      
      // Refetch user profile
      refetchProfile();
    },
    onError: () => {
      clearTokens();
    },
  });

  const clearTokens = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    authApi.clearAuthToken();
    setUser(null);
    setIsAuthenticated(false);
    queryClient.clear();
  };

  const handleLogin = async (credentials: LoginCredentials): Promise<void> => {
    await loginMutation.mutateAsync(credentials);
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // Ignore logout errors
    } finally {
      clearTokens();
      toast.success('Logged out successfully');
    }
  };

  const handleRefreshToken = async (): Promise<void> => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    await refreshTokenMutation.mutateAsync({ refresh_token: refreshToken });
  };

  // Set up automatic token refresh
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (isAuthenticated) {
      // Refresh token every 25 minutes (tokens expire in 30 minutes)
      intervalId = setInterval(() => {
        handleRefreshToken().catch(() => {
          // Silent fail, user will be logged out on next API call
        });
      }, 25 * 60 * 1000); // 25 minutes
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isAuthenticated]);

  // Set up axios interceptor for token refresh
  useEffect(() => {
    const setupInterceptor = () => {
      // Response interceptor to handle 401 errors
      const responseInterceptor = authApi.axiosInstance.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config;

          if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
              await handleRefreshToken();
              // Retry the original request with new token
              const newToken = localStorage.getItem('access_token');
              if (newToken) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return authApi.axiosInstance(originalRequest);
              }
            } catch (refreshError) {
              clearTokens();
              return Promise.reject(refreshError);
            }
          }

          return Promise.reject(error);
        }
      );

      return responseInterceptor;
    };

    const interceptorId = setupInterceptor();

    return () => {
      authApi.axiosInstance.interceptors.response.eject(interceptorId);
    };
  }, []);

  const contextValue: AuthContextType = {
    user,
    isAuthenticated,
    isLoading: !isInitialized || loginMutation.isLoading || refreshTokenMutation.isLoading,
    login: handleLogin,
    logout: handleLogout,
    refreshToken: handleRefreshToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};