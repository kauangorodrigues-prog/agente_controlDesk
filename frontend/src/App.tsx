import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Cobranca from "./pages/Cobranca";
import ControlDesk from "./pages/ControlDesk";
import Planejamento from "./pages/Planejamento";
import MIS from "./pages/MIS";
import Desenvolvimento from "./pages/Desenvolvimento";
import Infraestrutura from "./pages/Infraestrutura";
import LGPD from "./pages/LGPD";
import Usuarios from "./pages/Usuarios";

export default function App() {
  const { user, loading } = useAuth();

  if (loading)
    return (
      <div className="login-wrap">
        <div className="muted">Carregando…</div>
      </div>
    );

  if (!user) return <Login />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cobranca" element={<Cobranca />} />
        <Route path="/control-desk" element={<ControlDesk />} />
        <Route path="/planejamento" element={<Planejamento />} />
        <Route path="/mis" element={<MIS />} />
        <Route path="/desenvolvimento" element={<Desenvolvimento />} />
        <Route path="/infraestrutura" element={<Infraestrutura />} />
        <Route path="/lgpd" element={<LGPD />} />
        <Route path="/usuarios" element={<Usuarios />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
