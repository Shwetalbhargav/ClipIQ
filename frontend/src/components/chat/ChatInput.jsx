import { Send } from 'lucide-react'
import Button from '../ui/Button.jsx'

function ChatInput({ disabled, isStreaming, onChange, onSubmit, value }) {
  return (
    <form className="flex gap-2 border-t border-outline-variant p-3" onSubmit={onSubmit}>
      <label className="sr-only" htmlFor="chat-message">
        Ask about this comparison
      </label>
      <input
        id="chat-message"
        className="min-w-0 flex-1 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none placeholder:text-outline focus:ring-2 focus:ring-primary/70 disabled:cursor-not-allowed disabled:opacity-60"
        placeholder="Ask why one video performed better"
        value={value}
        disabled={disabled || isStreaming}
        onChange={onChange}
      />
      <Button
        type="submit"
        size="icon"
        variant="primary"
        disabled={disabled || isStreaming || !value.trim()}
        aria-label="Send chat message"
      >
        <Send className="h-4 w-4" aria-hidden="true" />
      </Button>
    </form>
  )
}

export default ChatInput
