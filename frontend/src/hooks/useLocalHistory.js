import { useCallback, useState } from 'react'

const STORAGE_KEY = 'clipiq.recentComparisons'

function readHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function useLocalHistory() {
  const [items, setItems] = useState(readHistory)

  const addItem = useCallback((comparison) => {
    const nextItem = {
      id: comparison.id,
      status: comparison.status,
      createdAt: comparison.createdAt || new Date().toISOString(),
      youtubeCreator: comparison.videoA?.creator || null,
      instagramCreator: comparison.videoB?.creator || null,
    }

    setItems((current) => {
      const next = [nextItem, ...current.filter((item) => item.id !== nextItem.id)].slice(0, 8)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  return { items, addItem }
}
