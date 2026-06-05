function EmptyState({ action, children, className = '', icon: Icon, title }) {
  return (
    <section className={`rounded-xl border border-dashed border-outline-variant bg-surface-container p-8 text-center ${className}`}>
      {Icon && <Icon className="mx-auto h-7 w-7 text-on-surface-variant" aria-hidden="true" />}
      <h2 className="mt-3 text-lg font-semibold text-on-surface">{title}</h2>
      {children && <div className="mt-2 text-sm text-on-surface-variant">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </section>
  )
}

export default EmptyState
