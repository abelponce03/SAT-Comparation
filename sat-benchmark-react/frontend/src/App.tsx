import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Solvers from './pages/Solvers'
import Benchmarks from './pages/Benchmarks'
import Experiments from './pages/Experiments'
import ExperimentDetail from './pages/ExperimentDetail'
import Analysis from './pages/Analysis'
import Visualization from './pages/Visualization'
import SATModeler from './pages/SATModeler'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="solvers" element={<Solvers />} />
        <Route path="benchmarks" element={<Benchmarks />} />
        <Route path="experiments" element={<Experiments />} />
        <Route path="experiments/:id" element={<ExperimentDetail />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="visualization" element={<Visualization />} />
        <Route path="modeler" element={<SATModeler />} />
      </Route>
    </Routes>
  )
}

export default App
