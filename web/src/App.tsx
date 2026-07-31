import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router'
import MainLayout from './components/MainLayout'

const Login = lazy(() => import('./pages/Login'))
const NotFound = lazy(() => import('./pages/NotFound'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Tickets = lazy(() => import('./pages/Tickets'))
const ChatIA = lazy(() => import('./pages/ChatIA'))
const Incidentes = lazy(() => import('./pages/Incidentes'))
const Relatorios = lazy(() => import('./pages/Relatorios'))
const Configuracoes = lazy(() => import('./pages/Configuracoes'))

function RouteFallback() {
  return (
    <div className="flex h-screen items-center justify-center bg-[#0A0A0A]">
      <div className="w-8 h-8 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<MainLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tickets" element={<Tickets />} />
          <Route path="/chat" element={<ChatIA />} />
          <Route path="/incidentes" element={<Incidentes />} />
          <Route path="/relatorios" element={<Relatorios />} />
          <Route path="/configuracoes" element={<Configuracoes />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}
