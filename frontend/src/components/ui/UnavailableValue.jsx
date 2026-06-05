import { UNAVAILABLE_LABEL } from '../../constants/app.js'

function isUnavailable(value) {
  return value === null || value === undefined || value === ''
}

function UnavailableValue({ as: Element = 'span', children, className = '', value }) {
  const displayValue = children ?? value

  if (isUnavailable(displayValue)) {
    return <Element className={`${className} font-semibold text-error italic`}>{UNAVAILABLE_LABEL}</Element>
  }

  return <Element className={className}>{displayValue}</Element>
}

export default UnavailableValue
