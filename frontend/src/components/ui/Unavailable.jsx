import { UNAVAILABLE_LABEL } from '../../constants/app.js'

function Unavailable({ label = UNAVAILABLE_LABEL }) {
  return <span className="text-on-surface-variant">{label}</span>
}

export default Unavailable
