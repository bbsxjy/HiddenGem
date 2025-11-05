import { Bell, User, LogOut, Wifi, WifiOff, Activity, Menu } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { useRealtimeStore } from '@/store/useRealtimeStore';
import { useUIStore } from '@/store/useUIStore';
import { useQuery } from '@tanstack/react-query';
import { checkHealth } from '@/api/health';
import clsx from 'clsx';

export function Header() {
  const { user, logout } = useAuthStore();
  const { wsConnected } = useRealtimeStore();
  const { setSidebarOpen } = useUIStore();

  // Check backend API health
  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 10000, // Check every 10 seconds
    retry: 1,
  });

  const isBackendConnected = !isError && health?.status === 'healthy';

  const handleLogout = () => {
    if (window.confirm('确定要退出登录吗？')) {
      logout();
    }
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 px-3 sm:px-6 flex items-center justify-between">
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Mobile: hamburger menu */}
        <button
          onClick={() => setSidebarOpen(true)}
          className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="打开菜单"
        >
          <Menu size={20} />
        </button>

        <h2 className="text-base sm:text-lg font-semibold text-text-primary">
          量化交易系统
        </h2>

        {/* Backend API status - hidden on small mobile */}
        <div
          className={clsx(
            'hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
            isBackendConnected
              ? 'bg-green-100 text-green-700'
              : 'bg-red-100 text-red-700'
          )}
          title={isBackendConnected ? `后端服务正常 (${health?.version})` : '后端服务连接失败'}
        >
          <Activity size={12} className={isBackendConnected ? 'animate-pulse' : ''} />
          <span className="hidden md:inline">{isBackendConnected ? '后端正常' : '后端断开'}</span>
        </div>

        {/* WebSocket connection status - hidden on mobile */}
        <div
          className={clsx(
            'hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
            wsConnected
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-600'
          )}
          title={wsConnected ? 'WebSocket已连接' : 'WebSocket未连接'}
        >
          {wsConnected ? (
            <>
              <Wifi size={12} />
              <span>实时连接</span>
            </>
          ) : (
            <>
              <WifiOff size={12} />
              <span>已断开</span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Notifications */}
        <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors relative">
          <Bell size={20} className="hidden sm:block" />
          <Bell size={18} className="sm:hidden" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User menu */}
        <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-3 border-l border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
              <User size={16} className="text-primary-600" />
            </div>
            {/* User info - hidden on mobile */}
            <div className="hidden sm:block text-sm">
              <p className="font-medium text-text-primary">
                {user?.username || '未登录'}
              </p>
              <p className="text-text-secondary text-xs">{user?.role || ''}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="退出登录"
          >
            <LogOut size={18} className="hidden sm:block" />
            <LogOut size={16} className="sm:hidden" />
          </button>
        </div>
      </div>
    </header>
  );
}
