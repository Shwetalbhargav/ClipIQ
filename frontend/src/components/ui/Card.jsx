function Card({ as: Element = 'section', children, className = '' }) {
  return (
    <Element className={`rounded-xl border border-outline-variant bg-surface-container ${className}`}>
      {children}
    </Element>
  )
}

export function CardHeader({ children, className = '' }) {
  return <div className={`border-b border-outline-variant bg-surface-container-high px-4 py-3 ${className}`}>{children}</div>
}

export function CardBody({ children, className = '' }) {
  return <div className={`p-4 ${className}`}>{children}</div>
}

export default Card
