import { SearchX } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../components/ui/Card.jsx'
import { ROUTES } from '../constants/app.js'

function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-64px)] w-full max-w-3xl items-center px-4 py-10 sm:px-6">
      <Card className="w-full p-8">
        <SearchX className="h-7 w-7 text-error" aria-hidden="true" />
        <h1 className="mt-3 text-2xl font-bold text-on-surface">Page not found</h1>
        <p className="mt-2 text-sm text-on-surface-variant">This route does not exist in ClipIQ.</p>
        <Link
          to={ROUTES.create}
          className="mt-5 inline-flex rounded-lg bg-primary px-3 py-2 text-sm font-bold text-on-primary outline-none hover:brightness-105 focus-visible:ring-2 focus-visible:ring-primary/70"
        >
          Create comparison
        </Link>
      </Card>
    </div>
  )
}

export default NotFoundPage
