import { Tab } from '@headlessui/react';
import { ShoppingCart, MonitorPlay, Play } from 'lucide-react';
import { ManualTab } from '@/components/trading/tabs/ManualTab';
import { LiveMonitorTab } from '@/components/trading/tabs/LiveMonitorTab';
import { AutoTradingTab } from '@/components/trading/tabs/AutoTradingTab';
import clsx from 'clsx';

export function TradingHub() {
  const tabs = [
    {
      name: '手动交易',
      icon: ShoppingCart,
      component: ManualTab,
    },
    {
      name: '实时监控',
      icon: MonitorPlay,
      component: LiveMonitorTab,
    },
    {
      name: '自动交易',
      icon: Play,
      component: AutoTradingTab,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">交易中心</h1>
        <p className="text-text-secondary mt-1">执行交易、监控实时状态和管理自动交易</p>
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
