import {
  LayoutDashboard,
  TrendingUp,
  ShoppingCart,
  Brain,
  GraduationCap,
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
    label: '市场行情',
    path: '/market',
    icon: TrendingUp,
  },
  {
    label: '交易中心',
    path: '/trading',
    icon: ShoppingCart,
  },
  {
    label: '训练中心',
    path: '/training',
    icon: GraduationCap,
  },
  {
    label: '设置',
    path: '/settings',
    icon: Settings,
  },
];
