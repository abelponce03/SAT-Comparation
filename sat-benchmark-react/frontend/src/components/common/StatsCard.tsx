import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  description?: string;
  trend?: {
    value: number;
    positive: boolean;
  };
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
}

const colorClasses = {
  blue: {
    bg: 'bg-blue-500/5',
    icon: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    text: 'text-blue-400',
    glow: 'shadow-blue-500/10',
  },
  green: {
    bg: 'bg-green-500/5',
    icon: 'bg-green-500/10 text-green-400 border-green-500/20',
    text: 'text-green-400',
    glow: 'shadow-green-500/10',
  },
  yellow: {
    bg: 'bg-yellow-500/5',
    icon: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    text: 'text-yellow-400',
    glow: 'shadow-yellow-500/10',
  },
  red: {
    bg: 'bg-red-500/5',
    icon: 'bg-red-500/10 text-red-400 border-red-500/20',
    text: 'text-red-400',
    glow: 'shadow-red-500/10',
  },
  purple: {
    bg: 'bg-primary-500/5',
    icon: 'bg-primary-500/10 text-primary-400 border-primary-500/20',
    text: 'text-primary-400',
    glow: 'shadow-primary-500/10',
  },
};

export default function StatsCard({ 
  title, 
  value, 
  icon: Icon, 
  description,
  trend,
  color = 'purple' 
}: StatsCardProps) {
  const colors = colorClasses[color];
  
  return (
    <div className={clsx("card-hover group", colors.bg)}>
      <div className="card-body">
        <div className="flex items-center justify-between">
          <div className={clsx(
            "p-3 rounded-xl border transition-all duration-300 group-hover:scale-110",
            colors.icon
          )}>
            <Icon className="w-6 h-6" />
          </div>
          {trend && (
            <span className={clsx(
              "text-sm font-medium px-2 py-0.5 rounded-full",
              trend.positive 
                ? "text-green-400 bg-green-500/10" 
                : "text-red-400 bg-red-500/10"
            )}>
              {trend.positive ? '+' : ''}{trend.value}%
            </span>
          )}
        </div>
        
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-500">{title}</h3>
          <p className="mt-1 text-3xl font-bold text-white">{value}</p>
          {description && (
            <p className="mt-1 text-sm text-gray-500">{description}</p>
          )}
        </div>
      </div>
    </div>
  );
}
