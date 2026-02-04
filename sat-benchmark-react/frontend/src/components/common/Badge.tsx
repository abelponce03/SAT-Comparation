import clsx from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'error' | 'warning' | 'info' | 'gray' | 'purple';
  size?: 'sm' | 'md';
  animated?: boolean;
}

const variantClasses = {
  success: 'bg-green-500/10 text-green-400 border-green-500/30',
  error: 'bg-red-500/10 text-red-400 border-red-500/30',
  warning: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  gray: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  purple: 'bg-primary-500/10 text-primary-400 border-primary-500/30',
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
};

export default function Badge({ 
  children, 
  variant = 'gray', 
  size = 'sm',
  animated = false 
}: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center rounded-full font-medium border backdrop-blur-sm transition-all duration-200',
      variantClasses[variant],
      sizeClasses[size],
      animated && 'animate-pulse-slow'
    )}>
      {children}
    </span>
  );
}

// Specialized result badge
export function ResultBadge({ result }: { result: string }) {
  const variants: Record<string, 'success' | 'error' | 'warning' | 'info' | 'gray' | 'purple'> = {
    SAT: 'success',
    UNSAT: 'info',
    TIMEOUT: 'warning',
    MEMOUT: 'warning',
    ERROR: 'error',
    UNKNOWN: 'gray',
    PENDING: 'gray',
  };
  
  return (
    <Badge variant={variants[result] || 'gray'}>
      {result}
    </Badge>
  );
}

// Specialized status badge
export function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'success' | 'error' | 'warning' | 'info' | 'gray' | 'purple'> = {
    pending: 'gray',
    running: 'purple',
    completed: 'success',
    stopped: 'warning',
    error: 'error',
    ready: 'success',
    not_configured: 'warning',
  };
  
  const labels: Record<string, string> = {
    pending: 'Pendiente',
    running: 'Ejecutando',
    completed: 'Completado',
    stopped: 'Detenido',
    error: 'Error',
    ready: 'Listo',
    not_configured: 'Sin configurar',
  };
  
  const isAnimated = status === 'running';
  
  return (
    <Badge variant={variants[status] || 'gray'} animated={isAnimated}>
      {isAnimated && (
        <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 animate-pulse" />
      )}
      {labels[status] || status}
    </Badge>
  );
}
