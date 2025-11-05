import {
  LayoutDashboard,
  Activity,
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
    label: '设置',
    path: '/settings',
    icon: Settings,
  },
];
