import { useState, useRef, useEffect } from "react";
import { trpc } from "@/providers/trpc";
import {
  Send,
  Plus,
  MessageSquare,
  Bot,
  User,
  Ticket,
  ArrowUpRight,
  Loader2,
  Sparkles,
} from "lucide-react";

const suggestedPrompts = [
  "Como reiniciar o servidor?",
  "Analisar incidente recente",
  "Problema de acesso VPN",
  "Criar ticket de backup",
];

export default function ChatIA() {
  const [message, setMessage] = useState("");
  const [activeConversation, setActiveConversation] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const utils = trpc.useUtils();

  const { data: conversations } = trpc.chat.getConversations.useQuery();

  const { data: messages, isLoading: messagesLoading } = trpc.chat.getHistory.useQuery(
    { conversationId: activeConversation! },
    { enabled: !!activeConversation }
  );

  const createConversation = trpc.chat.createConversation.useMutation({
    onSuccess: (data) => {
      setActiveConversation(data.id);
      utils.chat.getConversations.invalidate();
    },
  });

  const sendMessage = trpc.chat.sendMessage.useMutation({
    onSuccess: () => {
      utils.chat.getHistory.invalidate({ conversationId: activeConversation! });
      utils.chat.getConversations.invalidate();
    },
  });

  const createTicketFromChat = trpc.chat.createTicketFromChat.useMutation({
    onSuccess: () => {
      utils.dashboard.stats.invalidate();
      utils.dashboard.recentTickets.invalidate();
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!message.trim()) return;

    if (!activeConversation) {
      createConversation.mutate(undefined, {
        onSuccess: (data) => {
          sendMessage.mutate({ conversationId: data.id, message: message.trim() });
          setMessage("");
        },
      });
    } else {
      sendMessage.mutate({ conversationId: activeConversation, message: message.trim() });
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setActiveConversation(null);
    setMessage("");
  };

  const handleSuggestedPrompt = (prompt: string) => {
    if (!activeConversation) {
      createConversation.mutate(undefined, {
        onSuccess: (data) => {
          sendMessage.mutate({ conversationId: data.id, message: prompt });
        },
      });
    } else {
      sendMessage.mutate({ conversationId: activeConversation, message: prompt });
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  return (
    <div className="flex h-[calc(100vh-112px)] -mx-4 -my-4 lg:-mx-6 lg:-my-6">
      {/* Conversations Sidebar */}
      <div className="w-[240px] bg-[#0D0D0D] border-r border-[#27272A] flex flex-col shrink-0 hidden md:flex">
        <div className="p-3 border-b border-[#27272A]">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nova Conversa
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {(conversations ?? []).map((conv) => (
            <button
              key={conv.id}
              onClick={() => setActiveConversation(conv.id)}
              className={`w-full flex items-start gap-2.5 px-3 py-2.5 rounded-lg text-left transition-colors ${
                activeConversation === conv.id
                  ? "bg-[#F97316]/10 text-[#F97316]"
                  : "text-[#94A3B8] hover:bg-[#1A1A1A] hover:text-[#F8FAFC]"
              }`}
            >
              <MessageSquare className="w-4 h-4 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{conv.title ?? `Conversa #${conv.id}`}</p>
                <p className="text-[10px] text-[#64748B] mt-0.5">
                  {conv.createdAt ? new Date(conv.createdAt).toLocaleDateString("pt-BR") : ""}
                </p>
              </div>
            </button>
          ))}

          {(!conversations || conversations.length === 0) && (
            <div className="text-center py-8 text-[#64748B]">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-xs">Nenhuma conversa</p>
            </div>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-[#0A0A0A] min-w-0">
        {/* Empty State */}
        {!activeConversation ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-[#F97316]/10 flex items-center justify-center mb-6 orange-glow">
              <Bot className="w-8 h-8 text-[#F97316]" />
            </div>
            <h2 className="text-xl font-semibold text-[#F8FAFC] mb-2">
              NexusAI Assistant
            </h2>
            <p className="text-sm text-[#94A3B8] mb-8 text-center max-w-md">
              Seu assistente virtual para operações de TI. Pergunte sobre problemas técnicos,
              crie tickets ou analise incidentes.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
              {[
                { icon: Sparkles, text: "Diagnosticar problema de rede" },
                { icon: Ticket, text: "Criar ticket de suporte" },
                { icon: Bot, text: "Como configurar VPN?" },
                { icon: ArrowUpRight, text: "Status dos sistemas" },
              ].map((item, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestedPrompt(item.text)}
                  className="flex items-center gap-3 p-3 bg-[#111111] border border-[#27272A] rounded-lg hover:border-[#F97316]/50 hover:bg-[#1A1A1A] transition-all text-left"
                >
                  <item.icon className="w-4 h-4 text-[#F97316] shrink-0" />
                  <span className="text-xs text-[#94A3B8]">{item.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 lg:px-8 py-6 space-y-6">
              {messagesLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-6 h-6 text-[#F97316] animate-spin" />
                </div>
              ) : (
                (messages ?? []).map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 message-enter ${
                      msg.role === "user" ? "flex-row-reverse" : ""
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                        msg.role === "assistant"
                          ? "bg-[#F97316]/20"
                          : "bg-[#27272A]"
                      }`}
                    >
                      {msg.role === "assistant" ? (
                        <Bot className="w-4 h-4 text-[#F97316]" />
                      ) : (
                        <User className="w-4 h-4 text-[#94A3B8]" />
                      )}
                    </div>

                    {/* Message Bubble */}
                    <div
                      className={`max-w-[80%] lg:max-w-[70%] rounded-xl px-4 py-3 ${
                        msg.role === "assistant"
                          ? "bg-[#111111] border-l-[3px] border-[#F97316] text-[#F8FAFC]"
                          : "bg-[#1A1A1A] text-[#F8FAFC]"
                      }`}
                    >
                      <div className="text-sm whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </div>
                      <p className="text-[10px] text-[#64748B] mt-2">
                        {msg.createdAt
                          ? new Date(msg.createdAt).toLocaleTimeString("pt-BR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : ""}
                      </p>
                    </div>
                  </div>
                ))
              )}

              {/* Typing indicator */}
              {sendMessage.isPending && (
                <div className="flex gap-3 message-enter">
                  <div className="w-8 h-8 rounded-full bg-[#F97316]/20 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-[#F97316]" />
                  </div>
                  <div className="bg-[#111111] border-l-[3px] border-[#F97316] rounded-xl px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#F97316] typing-dot" />
                      <span className="w-2 h-2 rounded-full bg-[#F97316] typing-dot" />
                      <span className="w-2 h-2 rounded-full bg-[#F97316] typing-dot" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Quick Actions */}
            <div className="px-4 lg:px-8 pb-2">
              <button
                onClick={() => activeConversation && createTicketFromChat.mutate({ conversationId: activeConversation })}
                disabled={createTicketFromChat.isPending}
                className="flex items-center gap-2 px-3 py-1.5 bg-[#111111] border border-[#27272A] rounded-full text-xs text-[#94A3B8] hover:text-[#F97316] hover:border-[#F97316]/30 transition-colors mb-2"
              >
                <Ticket className="w-3 h-3" />
                {createTicketFromChat.isPending ? "Criando ticket..." : "Criar ticket desta conversa"}
              </button>
            </div>
          </>
        )}

        {/* Input Area */}
        <div className="border-t border-[#27272A] px-4 lg:px-8 py-4">
          {/* Suggested Prompts */}
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1 scrollbar-none">
            {suggestedPrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleSuggestedPrompt(prompt)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#111111] border border-[#27272A] rounded-full text-xs text-[#94A3B8] hover:text-[#F97316] hover:border-[#F97316]/30 whitespace-nowrap transition-colors"
              >
                <Sparkles className="w-3 h-3" />
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Descreva seu problema ou pergunta..."
              rows={1}
              className="flex-1 bg-[#111111] border border-[#27272A] rounded-xl px-4 py-3 text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316] focus:ring-1 focus:ring-[#F97316]/20 resize-none transition-all outline-none min-h-[44px] max-h-[120px]"
            />
            <button
              onClick={handleSend}
              disabled={!message.trim() || sendMessage.isPending || createConversation.isPending}
              className="p-3 bg-[#F97316] hover:bg-[#EA580C] text-white rounded-xl transition-colors disabled:opacity-30 disabled:cursor-not-allowed orange-glow"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
