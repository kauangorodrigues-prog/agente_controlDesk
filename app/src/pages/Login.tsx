import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { Bot, Loader2, Lock, Mail, User as UserIcon } from "lucide-react";
import { trpc } from "@/providers/trpc";

type Mode = "login" | "register";

const DEMO_EMAIL = "admin@nexusai.com";
const DEMO_PASSWORD = "admin123";

export default function Login() {
  const navigate = useNavigate();
  const utils = trpc.useUtils();

  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onAuthSuccess = async () => {
    await utils.auth.me.invalidate();
    navigate("/");
  };

  const loginMutation = trpc.auth.login.useMutation({
    onSuccess: onAuthSuccess,
    onError: (e) => setError(e.message),
  });
  const registerMutation = trpc.auth.register.useMutation({
    onSuccess: onAuthSuccess,
    onError: (e) => setError(e.message),
  });

  const isPending = loginMutation.isPending || registerMutation.isPending;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode === "login") {
      loginMutation.mutate({ email, password });
    } else {
      registerMutation.mutate({ name, email, password });
    }
  };

  const fillDemo = () => {
    setMode("login");
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    setError(null);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] text-[#F8FAFC] p-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-[#F97316] flex items-center justify-center shadow-lg shadow-[#F97316]/20">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight">NexusAI</h1>
            <p className="text-sm text-[#64748B]">Control Desk</p>
          </div>
        </div>

        <div className="bg-[#0D0D0D] border border-[#27272A] rounded-2xl p-6 shadow-xl">
          <div className="flex gap-1 p-1 bg-[#111111] border border-[#27272A] rounded-lg mb-6">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setMode(m);
                  setError(null);
                }}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                  mode === m
                    ? "bg-[#F97316] text-white"
                    : "text-[#94A3B8] hover:text-[#F8FAFC]"
                }`}
              >
                {m === "login" ? "Entrar" : "Criar conta"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <Field
                icon={<UserIcon className="w-4 h-4" />}
                label="Nome"
                type="text"
                value={name}
                onChange={setName}
                placeholder="Seu nome"
                autoComplete="name"
                required
              />
            )}
            <Field
              icon={<Mail className="w-4 h-4" />}
              label="E-mail"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="voce@empresa.com"
              autoComplete="email"
              required
            />
            <Field
              icon={<Lock className="w-4 h-4" />}
              label="Senha"
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="••••••••"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />

            {error && (
              <p className="text-sm text-[#EF4444] bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isPending}
              className="w-full flex items-center justify-center gap-2 bg-[#F97316] hover:bg-[#EA6C0F] text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-60"
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === "login" ? "Entrar" : "Criar conta"}
            </button>
          </form>

          <button
            type="button"
            onClick={fillDemo}
            className="w-full mt-4 text-xs text-[#64748B] hover:text-[#94A3B8] transition-colors"
          >
            Usar conta de demonstração ({DEMO_EMAIL} / {DEMO_PASSWORD})
          </button>
        </div>
      </div>
    </div>
  );
}

type FieldProps = {
  icon: React.ReactNode;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
};

function Field({
  icon,
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  required,
}: FieldProps) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-[#94A3B8] mb-1.5 block">
        {label}
      </span>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B]">
          {icon}
        </span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          className="w-full bg-[#111111] border border-[#27272A] rounded-lg pl-9 pr-3 py-2.5 text-sm text-[#F8FAFC] placeholder:text-[#3F3F46] focus:outline-none focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316] transition-colors"
        />
      </div>
    </label>
  );
}
