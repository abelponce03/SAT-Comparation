interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

const sizeClasses = {
  sm: 'w-5 h-5',
  md: 'w-10 h-10',
  lg: 'w-16 h-16',
};

export default function LoadingSpinner({ size = 'md', text }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 animate-fade-in">
      <div className="relative">
        {/* Outer glow */}
        <div className={`${sizeClasses[size]} absolute inset-0 rounded-full bg-primary-600/20 blur-xl animate-pulse`} />
        {/* Spinner */}
        <div className={`${sizeClasses[size]} relative animate-spin rounded-full border-2 border-dark-700 border-t-primary-500 border-r-primary-500`} />
      </div>
      {text && (
        <p className="mt-6 text-sm text-gray-400 animate-pulse">{text}</p>
      )}
    </div>
  );
}
