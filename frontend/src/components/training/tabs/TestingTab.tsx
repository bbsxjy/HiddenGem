import { Tab } from '@headlessui/react';
import { Timer, Database } from 'lucide-react';
import { BacktestTab } from '@/components/training/tabs/BacktestTab';
import { MemoryBankTab } from '@/components/training/tabs/MemoryBankTab';
import clsx from 'clsx';

export function TestingTab() {
  const subtabs = [
    {
      name: '回测系统',
      icon: Timer,
      component: BacktestTab,
      description: '使用历史数据回测策略表现'
    },
    {
      name: 'Memory Bank',
      icon: Database,
      component: MemoryBankTab,
      description: '查看和管理Agent学习记录'
    },
  ];

  return (
    <div className="space-y-6">
      {/* Sub-tabs */}
      <Tab.Group>
        <Tab.List className="flex space-x-1 rounded-xl bg-gray-100 p-1">
          {subtabs.map((tab) => (
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
          {subtabs.map((tab, idx) => (
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
