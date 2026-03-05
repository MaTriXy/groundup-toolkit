"use client"

import { create } from "zustand"
import { ChatMessage } from "@/lib/types"

function generateId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

interface ChatState {
  messages: ChatMessage[]
  isStreaming: boolean
  isOpen: boolean
  serviceContext: string | null
  serviceContextName: string | null
  openChat: (context?: string, contextName?: string) => void
  closeChat: () => void
  addMessage: (message: ChatMessage) => void
  updateLastAssistantMessage: (content: string) => void
  setStreaming: (streaming: boolean) => void
  clearChat: () => void
  sendMessage: (content: string) => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  isOpen: false,
  serviceContext: null,
  serviceContextName: null,

  openChat: (context, contextName) =>
    set({ isOpen: true, serviceContext: context ?? null, serviceContextName: contextName ?? null }),

  closeChat: () => set({ isOpen: false }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateLastAssistantMessage: (content) =>
    set((state) => {
      const msgs = [...state.messages]
      const lastIdx = msgs.findLastIndex((m) => m.role === "assistant")
      if (lastIdx >= 0) {
        msgs[lastIdx] = { ...msgs[lastIdx], content }
      }
      return { messages: msgs }
    }),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  clearChat: () => set({ messages: [], serviceContext: null, serviceContextName: null }),

  sendMessage: async (content) => {
    const { serviceContext, addMessage, updateLastAssistantMessage, setStreaming } = get()

    const userMsg: ChatMessage = {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date(),
      serviceContext: serviceContext ?? undefined,
    }
    addMessage(userMsg)

    const assistantMsg: ChatMessage = {
      id: generateId(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
    }
    addMessage(assistantMsg)
    setStreaming(true)

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          context: serviceContext,
          history: get().messages.slice(0, -1),
        }),
      })

      if (!res.ok) throw new Error("Chat request failed")

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let fullText = ""

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          fullText += decoder.decode(value, { stream: true })
          updateLastAssistantMessage(fullText)
        }
      }
    } catch {
      updateLastAssistantMessage("Sorry, something went wrong. Please try again.")
    } finally {
      setStreaming(false)
    }
  },
}))
