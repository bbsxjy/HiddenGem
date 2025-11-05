import {
  // LayoutDashboard,
  TrendingUp,
  // Briefcase,
  // ShoppingCart,
  Activity,
  Target,
  Settings,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  // {
  //   label: '仪表盘',
  //   path: '/dashboard',
  //   icon: LayoutDashboard,
  // },
  {
    label: '个股查询',
    path: '/market',
    icon: TrendingUp,
  },
  // {
  //   label: '投资组合',
  //   path: '/portfolio',
  //   icon: Briefcase,
  // },
  // {
  //   label: '交易',
  //   path: '/trading',
  //   icon: ShoppingCart,
  // },
  {
    label: '个股智能分析',
    path: '/agents',
    icon: Activity,
  },
  {
    label: '策略管理',
    path: '/strategy',
    icon: Target,
  },
  {
    label: '设置',
    path: '/settings',
    icon: Settings,
  },
];
