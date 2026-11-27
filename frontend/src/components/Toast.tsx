interface ToastProps {
  message: string
  textSize?: string
}

function Toast({ message, textSize = 'text-[13px]' }: ToastProps) {
  if (!message) return null

  return (
    <div
      role="status"
      className={`fixed bottom-6 right-4 z-50 animate-fade-up rounded-md border border-primary-500/30 bg-background-900/95 px-4 py-3 ${textSize} text-foreground-100 shadow-panel backdrop-blur-md md:right-8`}
    >
      <span className="flex items-center gap-2">
        <i className="ri-checkbox-circle-line text-primary-400" />
        {message}
      </span>
    </div>
  )
}

export default Toast
