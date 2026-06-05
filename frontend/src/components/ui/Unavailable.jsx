import { UNAVAILABLE_LABEL } from '../../constants/app.js'
import UnavailableValue from './UnavailableValue.jsx'

function Unavailable({ label = UNAVAILABLE_LABEL }) {
  return <UnavailableValue value={label} />
}

export default Unavailable
