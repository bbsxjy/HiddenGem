import { Tab } from '@headlessui/react';
import { Play, History } from 'lucide-react';
import { AutoTradingTab } from '@/components/trading/tabs/AutoTradingTab';
import { TradingHistoryTab } from '@/components/trading/tabs/TradingHistoryTab';
import clsx from 'clsx';

export function TradingHub() {
  const tabs = [
    {
      name: '自动交易',
      icon: Play,
      component: AutoTradingTab,
      description: '启动后显示实时监控，停止后显示控制面板'
    },
    {
      name: '交易历史',
      icon: History,
      component: TradingHistoryTab,
      description: '查看历史交易记录和统计'
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">交易中心</h1>
        <p className="text-text-secondary mt-1">自动交易系统与历史交易记录</p>
      </div>

      {/* Tabs */}
      <Tab.Group>
        <Tab.List className="flex space-x-1 rounded-xl bg-gray-100 p-1">
          {tabs.map((tab) => (
            <Tab
              key={tab.name}
              className={({ selected }) =>
                clsx(
                  'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
                  'ring-white ring-opacity-60 ring-offset-2 ring-offset-primary-400 focus:outline-none focus:ring-2',
                  selected
                    ? 'bg-white text-primary-700 shadow'
                    : 'text-text-secondary hover:bg-white/[0.12] hover:text-text-primary'
                )
              }
            >
              <div className="flex items-center justify-center gap-2">
                <tab.icon size={18} />
                <span>{tab.name}</span>
              </div>
            </Tab>
          ))}
        </Tab.List>
        <Tab.Panels className="mt-6">
          {tabs.map((tab, idx) => (
            <Tab.Panel
              key={idx}
              className={clsx(
                'rounded-xl bg-white',
                'ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2'
              )}
            >
              <tab.component />
            </Tab.Panel>
          ))}
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
}
