import React, { createContext, useState, useEffect, useContext } from 'react';

export interface User {
  id: number;
  username: string;
  role: string;
}

export interface ClassItem {
  id: number;
  class_name: string;
  created_at: string;
}

interface AppContextType {
  user: User | null;
  token: string | null;
  permissions: string[];
  selectedClassId: number | null;
  classes: ClassItem[];
  isLoadingClasses: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setSelectedClassId: (classId: number | null) => void;
  fetchClasses: () => Promise<void>;
  fetchWithAuth: (endpoint: string, options?: RequestInit) => Promise<any>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const API_BASE_URL = 'http://127.0.0.1:8000';

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [selectedClassId, setSelectedClassIdState] = useState<number | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [isLoadingClasses, setIsLoadingClasses] = useState(false);

  // Phục hồi session khi tải trang
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    const savedPermissions = localStorage.getItem('permissions');
    const savedClassId = localStorage.getItem('selectedClassId');

    if (savedToken && savedUser && savedPermissions) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      setPermissions(JSON.parse(savedPermissions));
      if (savedClassId) {
        setSelectedClassIdState(Number(savedClassId));
      }
    }
  }, []);

  // Lưu selected class id vào localStorage
  const setSelectedClassId = (classId: number | null) => {
    setSelectedClassIdState(classId);
    if (classId) {
      localStorage.setItem('selectedClassId', String(classId));
    } else {
      localStorage.removeItem('selectedClassId');
    }
  };

  const fetchWithAuth = async (endpoint: string, options: RequestInit = {}) => {
    const activeToken = token || localStorage.getItem('token');
    if (!activeToken) {
      throw new Error('Chưa đăng nhập.');
    }

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
      'Authorization': `Bearer ${activeToken}`
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });

    if (response.status === 401) {
      logout();
      throw new Error('Phiên đăng nhập đã hết hạn.');
    }

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || 'Lỗi kết nối máy chủ API.');
    }

    // Nếu endpoint xuất CSV hoặc file, trả về trực tiếp blob/response thay vì JSON
    if (endpoint.includes('/export.csv') || endpoint.includes('/template.csv')) {
      return response;
    }

    return response.json();
  };

  const fetchClasses = async () => {
    setIsLoadingClasses(true);
    try {
      const data = await fetchWithAuth('/api/classes');
      setClasses(data.classes);
      
      // Nếu chưa chọn lớp nào mà danh sách có lớp, chọn lớp đầu tiên
      const savedClassId = localStorage.getItem('selectedClassId');
      if (!savedClassId && data.classes.length > 0) {
        setSelectedClassId(data.classes[0].id);
      }
    } catch (err) {
      console.error('Lỗi tải danh sách lớp:', err);
    } finally {
      setIsLoadingClasses(false);
    }
  };

  const login = async (username: string, password: string) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || 'Thông tin đăng nhập không hợp lệ.');
    }

    const data = await response.json();
    setToken(data.token);
    setUser(data.user);
    setPermissions(data.permissions);

    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    localStorage.setItem('permissions', JSON.stringify(data.permissions));
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setPermissions([]);
    setSelectedClassId(null);
    localStorage.clear();
  };

  useEffect(() => {
    if (token) {
      fetchClasses();
    }
  }, [token]);

  return (
    <AppContext.Provider value={{
      user,
      token,
      permissions,
      selectedClassId,
      classes,
      isLoadingClasses,
      login,
      logout,
      setSelectedClassId,
      fetchClasses,
      fetchWithAuth
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp phải được sử dụng bên trong AppProvider');
  }
  return context;
};
