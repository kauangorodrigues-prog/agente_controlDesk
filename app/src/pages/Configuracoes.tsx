import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import {
  User,
  Bell,
  Monitor,
  Shield,
  Save,
  Check,
  Smartphone,
  Globe,
  Moon,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";

export default function Configuracoes() {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);

  const [profile, setProfile] = useState({
    name: user?.name ?? "Administrador",
    email: user?.email ?? "admin@nexusai.com",
    role: "Administrador de TI",
    phone: "+55 (11) 98765-4321",
    department: "Tecnologia",
  });

  const [notifications, setNotifications] = useState({
    ticketAssigned: true,
    ticketUpdated: true,
    criticalIncident: true,
    dailyReport: false,
    systemAlerts: true,
  });

  const [appearance, setAppearance] = useState({
    theme: "dark",
    density: "default",
  });

  const handleSaveProfile = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-4xl">
      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="bg-[#111111] border border-[#27272A] p-1">
          <TabsTrigger
            value="profile"
            className="data-[state=active]:bg-[#F97316] data-[state=active]:text-white text-[#94A3B8] flex items-center gap-2"
          >
            <User className="w-3.5 h-3.5" />
            Perfil
          </TabsTrigger>
          <TabsTrigger
            value="notifications"
            className="data-[state=active]:bg-[#F97316] data-[state=active]:text-white text-[#94A3B8] flex items-center gap-2"
          >
            <Bell className="w-3.5 h-3.5" />
            Notificações
          </TabsTrigger>
          <TabsTrigger
            value="appearance"
            className="data-[state=active]:bg-[#F97316] data-[state=active]:text-white text-[#94A3B8] flex items-center gap-2"
          >
            <Monitor className="w-3.5 h-3.5" />
            Aparência
          </TabsTrigger>
          <TabsTrigger
            value="security"
            className="data-[state=active]:bg-[#F97316] data-[state=active]:text-white text-[#94A3B8] flex items-center gap-2"
          >
            <Shield className="w-3.5 h-3.5" />
            Segurança
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-6">
          <div className="bg-[#111111] border border-[#27272A] rounded-lg p-6">
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-1">Informações do Perfil</h3>
            <p className="text-sm text-[#94A3B8] mb-6">Atualize suas informações pessoais</p>

            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 rounded-full bg-[#F97316]/20 flex items-center justify-center">
                <User className="w-8 h-8 text-[#F97316]" />
              </div>
              <div>
                <p className="text-sm font-medium text-[#F8FAFC]">{profile.name}</p>
                <p className="text-xs text-[#64748B]">{profile.role}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-sm text-[#94A3B8]">Nome</Label>
                <Input
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Email</Label>
                <Input
                  value={profile.email}
                  disabled
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#64748B] cursor-not-allowed"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Cargo</Label>
                <Input
                  value={profile.role}
                  onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Telefone</Label>
                <Input
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Departamento</Label>
                <Input
                  value={profile.department}
                  onChange={(e) => setProfile({ ...profile, department: e.target.value })}
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] focus:border-[#F97316]"
                />
              </div>
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={handleSaveProfile}
                className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors"
              >
                {saved ? (
                  <>
                    <Check className="w-4 h-4" />
                    Salvo!
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Salvar Alterações
                  </>
                )}
              </button>
            </div>
          </div>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          <div className="bg-[#111111] border border-[#27272A] rounded-lg p-6">
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-1">Configurações de Notificações</h3>
            <p className="text-sm text-[#94A3B8] mb-6">Escolha quais notificações deseja receber</p>

            <div className="space-y-4">
              {[
                {
                  key: "ticketAssigned",
                  label: "Novo ticket atribuído",
                  description: "Receber notificação quando um ticket for atribuído a você",
                },
                {
                  key: "ticketUpdated",
                  label: "Ticket atualizado",
                  description: "Receber notificação quando houver atualização em seus tickets",
                },
                {
                  key: "criticalIncident",
                  label: "Incidente crítico",
                  description: "Receber alerta imediato para incidentes de alta prioridade",
                },
                {
                  key: "dailyReport",
                  label: "Relatório diário",
                  description: "Receber resumo diário das atividades do control desk",
                },
                {
                  key: "systemAlerts",
                  label: "Alertas do sistema",
                  description: "Notificações sobre status e manutenção dos sistemas",
                },
              ].map((item) => (
                <div
                  key={item.key}
                  className="flex items-start justify-between py-3 border-b border-[#27272A]/50 last:border-0"
                >
                  <div>
                    <p className="text-sm text-[#F8FAFC]">{item.label}</p>
                    <p className="text-xs text-[#64748B] mt-0.5">{item.description}</p>
                  </div>
                  <Switch
                    checked={notifications[item.key as keyof typeof notifications]}
                    onCheckedChange={(checked) =>
                      setNotifications({ ...notifications, [item.key]: checked })
                    }
                    className="data-[state=checked]:bg-[#F97316]"
                  />
                </div>
              ))}
            </div>
          </div>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance" className="space-y-6">
          <div className="bg-[#111111] border border-[#27272A] rounded-lg p-6">
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-1">Aparência</h3>
            <p className="text-sm text-[#94A3B8] mb-6">Personalize a interface do sistema</p>

            <div className="space-y-6">
              <div>
                <Label className="text-sm text-[#94A3B8] mb-3 block">Tema</Label>
                <div className="flex gap-3">
                  <button className="flex items-center gap-2 px-4 py-3 bg-[#F97316]/10 border border-[#F97316] text-[#F97316] rounded-lg text-sm">
                    <Moon className="w-4 h-4" />
                    Escuro
                  </button>
                </div>
                <p className="text-xs text-[#64748B] mt-2">Tema escuro é o único disponível nesta versão</p>
              </div>

              <div>
                <Label className="text-sm text-[#94A3B8] mb-3 block">Densidade da Interface</Label>
                <div className="flex gap-3">
                  {["compact", "default", "comfortable"].map((density) => (
                    <button
                      key={density}
                      onClick={() => setAppearance({ ...appearance, density })}
                      className={`px-4 py-2.5 rounded-lg text-sm border transition-colors ${
                        appearance.density === density
                          ? "bg-[#F97316]/10 border-[#F97316] text-[#F97316]"
                          : "bg-[#0A0A0A] border-[#27272A] text-[#94A3B8] hover:text-[#F8FAFC]"
                      }`}
                    >
                      {density === "compact" ? "Compacto" : density === "default" ? "Padrão" : "Confortável"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <Label className="text-sm text-[#94A3B8] mb-3 block">Cor de Destaque</Label>
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#F97316] ring-2 ring-[#F97316] ring-offset-2 ring-offset-[#111111] cursor-pointer" />
                  <div className="w-10 h-10 rounded-full bg-[#3B82F6] opacity-30 cursor-not-allowed" />
                  <div className="w-10 h-10 rounded-full bg-[#22C55E] opacity-30 cursor-not-allowed" />
                  <div className="w-10 h-10 rounded-full bg-[#8B5CF6] opacity-30 cursor-not-allowed" />
                </div>
                <p className="text-xs text-[#64748B] mt-2">Laranja é a cor padrão do NexusAI</p>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-6">
          <div className="bg-[#111111] border border-[#27272A] rounded-lg p-6">
            <h3 className="text-base font-semibold text-[#F8FAFC] mb-1">Segurança</h3>
            <p className="text-sm text-[#94A3B8] mb-6">Gerencie sua senha e sessões ativas</p>

            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-medium text-[#F8FAFC] mb-4">Alterar Senha</h4>
                <div className="space-y-3 max-w-md">
                  <div>
                    <Label className="text-sm text-[#94A3B8]">Senha Atual</Label>
                    <Input
                      type="password"
                      placeholder="••••••••"
                      className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                    />
                  </div>
                  <div>
                    <Label className="text-sm text-[#94A3B8]">Nova Senha</Label>
                    <Input
                      type="password"
                      placeholder="••••••••"
                      className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                    />
                  </div>
                  <div>
                    <Label className="text-sm text-[#94A3B8]">Confirmar Nova Senha</Label>
                    <Input
                      type="password"
                      placeholder="••••••••"
                      className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                    />
                  </div>
                  <button className="px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors">
                    Alterar Senha
                  </button>
                </div>
              </div>

              <div className="border-t border-[#27272A] pt-6">
                <h4 className="text-sm font-medium text-[#F8FAFC] mb-4">Sessões Ativas</h4>
                <div className="space-y-3">
                  {[
                    { device: "Chrome - Windows", location: "São Paulo, BR", current: true, time: "Agora" },
                    { device: "Safari - macOS", location: "São Paulo, BR", current: false, time: "2 horas atrás" },
                  ].map((session, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-3 px-4 bg-[#0A0A0A] rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-[#1A1A1A] flex items-center justify-center">
                          {session.device.includes("Chrome") ? (
                            <Globe className="w-4 h-4 text-[#94A3B8]" />
                          ) : (
                            <Smartphone className="w-4 h-4 text-[#94A3B8]" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm text-[#F8FAFC]">
                            {session.device}
                            {session.current && (
                              <span className="ml-2 text-[10px] bg-[#22C55E]/10 text-[#22C55E] px-1.5 py-0.5 rounded-full">
                                Atual
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-[#64748B]">
                            {session.location} · {session.time}
                          </p>
                        </div>
                      </div>
                      {!session.current && (
                        <button className="text-xs text-[#EF4444] hover:text-[#DC2626] transition-colors">
                          Encerrar
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
