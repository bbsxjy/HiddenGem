import {
  LayoutDashboard,
  Activity,
  TrendingUp,
  Briefcase,
  ShoppingCart,
  LineChart,
  Brain,
  Timer,
  Settings,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  {
    label: '仪表盘',
    path: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    label: '智能分析',
    path: '/analysis',
    icon: Activity,
  },
  {
    label: '市场行情',
    path: '/market',
    icon: TrendingUp,
  },
  {
    label: '投资组合',
    path: '/portfolio',
    icon: Briefcase,
  },
  {
    label: '交易面板',
    path: '/trading',
    icon: ShoppingCart,
  },
  {
    label: '策略管理',
    path: '/strategy',
    icon: LineChart,
  },
  {
    label: 'Agent监控',
    path: '/agents',
    icon: Brain,
  },
  {
    label: '回测系统',
    path: '/backtest',
    icon: Timer,
  },
  {
    label: '设置',
    path: '/settings',
    icon: Settings,
  },
];
