import { Info, Trophy } from 'lucide-react'
import { compareEngagement } from '../../utils/engagement.js'
import { formatPercent } from '../../utils/formatters.js'
import Card, { CardBody, CardHeader } from '../ui/Card.jsx'
import UnavailableValue from '../ui/UnavailableValue.jsx'

function winnerLabel(winner) {
  if (winner === 'A') return 'Video A'
  if (winner === 'B') return 'Video B'
  if (winner === 'tie') return 'Tie'
  return null
}

function EngagementSummary({ comparison }) {
  const result = compareEngagement(comparison.videoA, comparison.videoB)
  const winner = winnerLabel(result.winner)
  const formula = '(likes + comments) / views * 100'

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold uppercase tracking-[0.18em] text-on-surface">Engagement summary</h2>
        <Info className="h-5 w-5 text-on-surface-variant" aria-hidden="true" />
      </CardHeader>
      <CardBody className="space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-on-surface-variant">Stronger performer</p>
            <p className="mt-1 flex items-center gap-2 text-3xl font-bold text-on-surface">
              {winner && winner !== 'Tie' && <Trophy className="h-6 w-6 text-tertiary" aria-hidden="true" />}
              <UnavailableValue value={winner} />
            </p>
          </div>
          <div className="sm:text-right">
            <p className="text-sm font-semibold text-on-surface-variant">Engagement delta</p>
            <p className="mt-1 text-2xl font-bold text-tertiary">
              <UnavailableValue value={result.delta === null ? null : formatPercent(result.delta)} />
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">Engagement formula</p>
          <p className="mt-2 font-mono text-sm text-on-surface">{formula}</p>
        </div>

        {comparison.engagement?.summary && (
          <p className="rounded-lg border border-outline-variant bg-surface-container-low p-3 text-sm leading-6 text-on-surface-variant">
            {comparison.engagement.summary}
          </p>
        )}
      </CardBody>
    </Card>
  )
}

export default EngagementSummary
