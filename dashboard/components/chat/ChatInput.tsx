"use client"

import { useState, useRef, useCallback } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useChatStore } from "@/lib/store/chatStore"

const MAX_CHARS = 2000

export function ChatInput() {
  const [text, setText] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { sendMessage, isStreaming } = useChatStore()

  const handleSend = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return
    sendMessage(trimmed)
    setText("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }, [text, isStreaming, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    if (val.length <= MAX_CHARS) {
      setText(val)
    }
    // Auto-resize
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = "auto"
      ta.style.height = Math.min(ta.scrollHeight, 120) + "px"
    }
  }

  return (
    <div className="border-t border-border p-3">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? "Waiting for response..." : "Message Christina..."}
          disabled={isStreaming}
          rows={1}
          className="flex-1 resize-none bg-muted/50 rounded-lg px-3 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 disabled:opacity-50"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!text.trim() || isStreaming}
          className="h-9 w-9 shrink-0 rounded-lg"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex justify-end mt-1">
        <span className="text-[10px] text-muted-foreground">
          {text.length}/{MAX_CHARS}
        </span>
      </div>
    </div>
  )
}
