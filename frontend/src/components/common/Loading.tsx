import { Loader2 } from 'lucide-react';
import clsx from 'clsx';

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullScreen?: boolean;
  className?: string;
}

export function Loading({
  size = 'md',
  text,
  fullScreen = false,
  className,
}: LoadingProps) {
  const sizes = {
    sm: 16,
    md: 24,
    lg: 32,
  };

  const content = (
    <div className={clsx('flex flex-col items-center justify-center gap-3', className)}>
      <Loader2 className="animate-spin text-primary-500" size={sizes[size]} />
      {text && <p className="text-text-secondary text-sm">{text}</p>}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white bg-opacity-80 z-50">
        {content}
      </div>
    );
  }

  return content;
}

// Spinner only
export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <Loader2
      className={clsx('animate-spin text-primary-500', className)}
      size={size}
    />
  );
}

// Loading skeleton
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'animate-pulse bg-gray-200 rounded',
        className
      )}
    />
  );
}
