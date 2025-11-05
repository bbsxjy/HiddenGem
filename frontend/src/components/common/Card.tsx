import { type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  headerAction?: ReactNode;
  footer?: ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
}

export function Card({
  title,
  subtitle,
  headerAction,
  footer,
  children,
  padding = 'md',
  hoverable = false,
  className,
  ...props
}: CardProps) {
  const paddingStyles = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  return (
    <div
      className={clsx(
        'bg-white rounded-lg border border-gray-200 shadow-card',
        hoverable && 'hover:shadow-card-hover transition-shadow cursor-pointer',
        className
      )}
      {...props}
    >
      {(title || headerAction) && (
        <div
          className={clsx(
            'flex items-center justify-between border-b border-gray-200',
            paddingStyles[padding]
          )}
        >
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-text-primary">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-text-secondary mt-0.5">{subtitle}</p>
            )}
          </div>
          {headerAction && <div>{headerAction}</div>}
        </div>
      )}

      <div className={clsx(paddingStyles[padding])}>{children}</div>

      {footer && (
        <div
          className={clsx(
            'border-t border-gray-200',
            paddingStyles[padding]
          )}
        >
          {footer}
        </div>
      )}
    </div>
  );
}
