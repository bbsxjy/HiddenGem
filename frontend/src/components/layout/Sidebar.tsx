import { Link, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useUIStore } from '@/store/useUIStore';
import { NAV_ITEMS } from './navigation';

export function Sidebar() {
  const location = useLocation();
  const { sidebarCollapsed, sidebarOpen, toggleSidebarCollapse, setSidebarOpen } = useUIStore();

  const handleLinkClick = () => {
    // Close sidebar on mobile when clicking a link
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 h-screen bg-white border-r border-gray-200 transition-all duration-300 z-40',
        // Mobile: always full width when open, slide in/out
        'w-64 lg:w-auto',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        // Desktop: width based on collapsed state
        sidebarCollapsed ? 'lg:w-16' : 'lg:w-64'
      )}
    >
      {/* Logo & Controls */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
        {/* Logo: always visible on mobile, conditionally on desktop */}
        <h1 className={clsx(
          'text-xl font-bold text-primary-500',
          sidebarCollapsed && 'lg:hidden'  // Only hide on desktop when collapsed
        )}>
          HiddenGem
        </h1>

        {/* Desktop: collapse button */}
        <button
          onClick={toggleSidebarCollapse}
          className="hidden lg:block p-1 rounded-lg hover:bg-gray-100 transition-colors ml-auto"
          title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          {sidebarCollapsed ? (
            <ChevronRight size={20} />
          ) : (
            <ChevronLeft size={20} />
          )}
        </button>

        {/* Mobile: close button */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1 rounded-lg hover:bg-gray-100 transition-colors ml-auto"
          title="关闭菜单"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="py-4 space-y-1 overflow-y-auto h-[calc(100vh-4rem)]">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={handleLinkClick}
              className={clsx(
                'flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-600'
                  : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              <Icon size={20} className="flex-shrink-0" />
              {/* Label: always visible on mobile, conditionally on desktop */}
              <span className={clsx(
                'font-medium',
                sidebarCollapsed && 'lg:hidden'  // Only hide on desktop when collapsed
              )}>
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
