import { Routes, Route } from 'react-router'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Dashboard from './pages/Dashboard'
import Tickets from './pages/Tickets'
import ChatIA from './pages/ChatIA'
import Incidentes from './pages/Incidentes'
import Relatorios from './pages/Relatorios'
import Configuracoes from './pages/Configuracoes'
import BaseConhecimento from './pages/BaseConhecimento'
import Equipe from './pages/Equipe'
import Ativos from './pages/Ativos'
import SLA from './pages/SLA'
import MainLayout from './components/MainLayout'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/chat" element={<ChatIA />} />
        <Route path="/incidentes" element={<Incidentes />} />
        <Route path="/base-conhecimento" element={<BaseConhecimento />} />
        <Route path="/equipe" element={<Equipe />} />
        <Route path="/ativos" element={<Ativos />} />
        <Route path="/sla" element={<SLA />} />
        <Route path="/relatorios" element={<Relatorios />} />
        <Route path="/configuracoes" element={<Configuracoes />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
