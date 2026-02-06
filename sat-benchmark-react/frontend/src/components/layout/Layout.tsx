import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Cpu, 
  FileText, 
  FlaskConical,
  BarChart3,
  LineChart,
  Menu,
  X,
  Github,
  BookOpen,
  Zap,
  ChevronRight,
  Brain,
  Microscope
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, description: 'Vista general' },
  { name: 'Solvers', href: '/solvers', icon: Cpu, description: 'Solvers disponibles' },
  { name: 'Benchmarks', href: '/benchmarks', icon: FileText, description: 'Instancias CNF' },
  { name: 'Experiments', href: '/experiments', icon: FlaskConical, description: 'Ejecutar pruebas' },
  { name: 'Analysis', href: '/analysis', icon: BarChart3, description: 'Métricas y estadísticas' },
  { name: 'Visualization', href: '/visualization', icon: LineChart, description: 'Gráficos y visuales' },
  { name: 'Rigorous Analysis', href: '/rigorous', icon: Microscope, description: 'Tests estadísticos avanzados' },
  { name: 'AI Assistant', href: '/ai', icon: Brain, description: 'Generar CNF con IA' },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-dark-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden animate-fade-in"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        "fixed top-0 left-0 z-50 h-full w-72 bg-dark-900/95 backdrop-blur-xl border-r border-dark-700/50 transform transition-all duration-300 ease-out lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Logo */}
        <div className="h-20 flex items-center justify-between px-6 border-b border-dark-700/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-accent-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-600/30">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg text-white">SAT Benchmark</span>
              <p className="text-xs text-gray-500">Suite v2.0</p>
            </div>
          </div>
          <button 
            className="lg:hidden p-2 hover:bg-dark-800 rounded-lg transition-colors"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          <p className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Navegación
          </p>
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) => clsx(
                "group flex items-center gap-3 px-3 py-3 rounded-xl font-medium transition-all duration-200",
                isActive 
                  ? "bg-gradient-to-r from-primary-600/20 to-accent-600/10 text-white border border-primary-600/30" 
                  : "text-gray-400 hover:bg-dark-800 hover:text-white"
              )}
              onClick={() => setSidebarOpen(false)}
            >
              <div className={clsx(
                "p-2 rounded-lg transition-colors",
                "group-hover:bg-primary-600/20"
              )}>
                <item.icon className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <span className="block">{item.name}</span>
                <span className="text-xs text-gray-500 group-hover:text-gray-400">{item.description}</span>
              </div>
              <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-dark-700/50">
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <a 
              href="https://github.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="p-2 hover:bg-dark-800 hover:text-white rounded-lg transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
            <a 
              href="/docs" 
              className="p-2 hover:bg-dark-800 hover:text-white rounded-lg transition-colors flex items-center gap-2"
            >
              <BookOpen className="w-5 h-5" />
              <span>Docs</span>
            </a>
          </div>
          <div className="mt-4 p-3 bg-dark-800/50 rounded-lg border border-dark-700/50">
            <p className="text-xs text-gray-500">
              Thesis Project · Abel
            </p>
            <p className="text-xs text-primary-400 mt-1">
              Comparative Analysis of SAT Solvers
            </p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Top bar */}
        <header className="h-16 bg-dark-900/80 backdrop-blur-md border-b border-dark-700/50 flex items-center justify-between px-4 lg:px-8 sticky top-0 z-30">
          <button 
            className="lg:hidden p-2 hover:bg-dark-800 rounded-lg transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5 text-gray-400" />
          </button>
          
          <div className="flex-1 lg:hidden" />
          
          <div className="hidden lg:flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-sm text-gray-400">
              Sistema operativo
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-dark-800 rounded-lg border border-dark-700/50">
              <span className="text-xs text-gray-500">
                {new Date().toLocaleDateString('es-ES', { 
                  weekday: 'short', 
                  month: 'short', 
                  day: 'numeric' 
                })}
              </span>
              <span className="text-xs text-primary-400 font-mono">
                {new Date().toLocaleTimeString('es-ES', { 
                  hour: '2-digit', 
                  minute: '2-digit'
                })}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-8 animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
