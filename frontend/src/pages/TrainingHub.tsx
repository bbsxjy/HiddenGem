import { Tab } from '@headlessui/react';
import { GraduationCap, Timer, Database } from 'lucide-react';
import { BacktestTab } from '@/components/training/tabs/BacktestTab';
import { MemoryBankTab } from '@/components/training/tabs/MemoryBankTab';
import clsx from 'clsx';

export function TrainingHub() {
  const tabs = [
    {
      name: '回测系统',
      icon: Timer,
      component: BacktestTab,
    },
    {
      name: 'Memory Bank',
      icon: Database,
      component: MemoryBankTab,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
          <GraduationCap className="text-primary-500" size={32} />
          训练中心
        </h1>
        <p className="text-text-secondary mt-1">
          回测策略表现、查看Agent学习记录
        </p>
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
