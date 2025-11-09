import { type ReactNode } from 'react';
import clsx from 'clsx';

interface Column<T> {
  key?: string;
  header: string;
  accessor?: keyof T;
  cell?: (value: any, row: T) => ReactNode;
  render?: (item: T) => ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
  sortable?: boolean;
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor?: (item: T) => string | number;
  onRowClick?: (item: T) => void;
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
}

export function Table<T extends Record<string, any>>({
  data,
  columns,
  keyExtractor,
  onRowClick,
  loading = false,
  emptyMessage = '暂无数据',
  className,
}: TableProps<T>) {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  // Default key extractor using id field or index
  const getKey = (item: T, index: number): string | number => {
    if (keyExtractor) {
      return keyExtractor(item);
    }
    return item.id !== undefined ? item.id : index;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-text-secondary">加载中...</div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-text-secondary">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={clsx('overflow-x-auto', className)}>
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {columns.map((column, index) => (
              <th
                key={column.key || `col-header-${index}`}
                className={clsx(
                  'px-4 py-3 text-sm font-semibold text-text-primary',
                  alignClasses[column.align || 'left']
                )}
                style={{ width: column.width }}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.map((item, rowIndex) => (
            <tr
              key={getKey(item, rowIndex)}
              className={clsx(
                'hover:bg-gray-50 transition-colors',
                onRowClick && 'cursor-pointer'
              )}
              onClick={() => onRowClick?.(item)}
            >
              {columns.map((column, colIndex) => {
                let content: ReactNode;

                if (column.render) {
                  // Old API: render function
                  content = column.render(item);
                } else if (column.cell && column.accessor) {
                  // New API: cell function with accessor
                  const value = item[column.accessor];
                  content = column.cell(value, item);
                } else if (column.accessor) {
                  // Default: just show the value
                  content = item[column.accessor];
                } else if (column.key) {
                  // Fallback to key
                  content = item[column.key];
                }

                return (
                  <td
                    key={column.key || `col-${rowIndex}-${colIndex}`}
                    className={clsx(
                      'px-4 py-3 text-sm text-text-primary',
                      alignClasses[column.align || 'left']
                    )}
                  >
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
