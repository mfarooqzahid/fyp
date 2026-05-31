import React from 'react'
import AddSourceModal from './components/AddSourceModal'
import Dashboard from './components/Dashboard'
import Icon from './components/Icon'
import Sidebar from './components/Sidebar'
import { createSource, fetchSources, deleteSource, fetchRushAlerts, updateSource } from './services/sourcesApi'

function playRushBeep() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext
    if (!AudioContext) return

    const audioContext = new AudioContext()
    const playTone = (startTime, frequency) => {
      const oscillator = audioContext.createOscillator()
      const gain = audioContext.createGain()

      oscillator.type = 'square'
      oscillator.frequency.setValueAtTime(frequency, startTime)
      gain.gain.setValueAtTime(0.001, startTime)
      gain.gain.exponentialRampToValueAtTime(0.16, startTime + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.28)

      oscillator.connect(gain)
      gain.connect(audioContext.destination)
      oscillator.start(startTime)
      oscillator.stop(startTime + 0.3)
      return oscillator
    }

    const firstTone = playTone(audioContext.currentTime, 880)
    playTone(audioContext.currentTime + 0.36, 1040)
    playTone(audioContext.currentTime + 0.72, 880)
    firstTone.onended = () => window.setTimeout(() => audioContext.close().catch(() => {}), 1200)
  } catch (error) {
    console.debug('Rush alert sound unavailable:', error)
  }
}

function formatAlertDetail(alert) {
  const current = Number(alert.current) || 0
  const ratio = Number(alert.ratio) || 0
  const windowMinutes = Number(alert.window_minutes) || 10
  return `${current} people, ${ratio.toFixed(2)}x average in last ${windowMinutes} minutes`
}

export default function App() {
  const [sources, setSources] = React.useState([])
  const [selectedSource, setSelectedSource] = React.useState('')
  const [isAddSourceOpen, setIsAddSourceOpen] = React.useState(false)
  const [isLoadingSources, setIsLoadingSources] = React.useState(true)
  const [sourceLoadError, setSourceLoadError] = React.useState('')
  const [isSavingSource, setIsSavingSource] = React.useState(false)
  const [sourceSaveError, setSourceSaveError] = React.useState('')
  const [rushToasts, setRushToasts] = React.useState([])
  const activeRushCamerasRef = React.useRef(new Set())
  const lastRushBeepAtRef = React.useRef(0)

  React.useEffect(() => {
    loadSources()
  }, [])

  React.useEffect(() => {
    let isActive = true

    async function checkRushAlerts() {
      try {
        const alerts = await fetchRushAlerts()
        if (!isActive) return

        const activeAlerts = alerts.filter((alert) => alert.active && alert.status === 'RUSH ALERT')
        const activeCameraIds = new Set(activeAlerts.map((alert) => alert.camera_id))
        const hasNewRushAlert = activeAlerts.some((alert) => !activeRushCamerasRef.current.has(alert.camera_id))

        activeRushCamerasRef.current = activeCameraIds

        if (activeAlerts.length > 0) {
          const now = Date.now()
          if (hasNewRushAlert || now - lastRushBeepAtRef.current > 30000) {
            playRushBeep()
            lastRushBeepAtRef.current = now
          }
        }

        setRushToasts(
          activeAlerts.map((alert) => ({
            id: alert.camera_id,
            title: `Abnormal activity detected at ${alert.title || alert.camera_id}`,
            detail: formatAlertDetail(alert),
          }))
        )
      } catch (error) {
        console.error('Failed to fetch rush alerts:', error)
      }
    }

    checkRushAlerts()
    const intervalId = window.setInterval(checkRushAlerts, 10000)

    return () => {
      isActive = false
      window.clearInterval(intervalId)
    }
  }, [])

  function dismissRushToast(toastId) {
    setRushToasts((currentToasts) => currentToasts.filter((toast) => toast.id !== toastId))
  }

  async function loadSources() {
    setIsLoadingSources(true)
    setSourceLoadError('')

    try {
      const dbSources = await fetchSources()
      setSources(dbSources)
      setSelectedSource((currentSelected) => {
        if (dbSources.some((source) => source.id === currentSelected)) {
          return currentSelected
        }

        return dbSources[0]?.id || ''
      })
    } catch (error) {
      setSourceLoadError(error.message)
    } finally {
      setIsLoadingSources(false)
    }
  }

  async function handleAddSource(source) {
    setIsSavingSource(true)
    setSourceSaveError('')

    try {
      const createdSource = await createSource(source)
      setSources((currentSources) => [...currentSources, createdSource])
      setSelectedSource(createdSource.id)
      setIsAddSourceOpen(false)
    } catch (error) {
      setSourceSaveError(error.message)
    } finally {
      setIsSavingSource(false)
    }
  }

  async function handleDeleteSource(sourceId) {
    try {
      await deleteSource(sourceId)
      setSources((currentSources) => {
        const nextSources = currentSources.filter((source) => source.id !== sourceId)
        setSelectedSource((currentSelected) => {
          if (currentSelected === sourceId) {
            return nextSources[0]?.id || ''
          }
          return currentSelected
        })
        return nextSources
      })
    } catch (error) {
      alert(`Failed to delete source: ${error.message}`)
    }
  }

  async function handleUpdateSource(sourceId, sourceData) {
    try {
      const updated = await updateSource(sourceId, sourceData)
      setSources((currentSources) =>
        currentSources.map((source) => (source.id === sourceId ? updated : source))
      )
    } catch (error) {
      console.error('Failed to update source:', error)
      throw error
    }
  }

  return (
    <div className="shell">
      <Sidebar
        sources={sources}
        selectedSource={selectedSource}
        onSelectSource={setSelectedSource}
        onAddSource={() => setIsAddSourceOpen(true)}
        isLoadingSources={isLoadingSources}
        sourceLoadError={sourceLoadError}
        onRetryLoad={loadSources}
      />

      <Dashboard
        sources={sources}
        selectedSource={selectedSource}
        onDeleteSource={handleDeleteSource}
        onUpdateSource={handleUpdateSource}
      />

      {isAddSourceOpen && (
        <AddSourceModal
          onClose={() => setIsAddSourceOpen(false)}
          onConfirm={handleAddSource}
          isSaving={isSavingSource}
          serverError={sourceSaveError}
        />
      )}

      {rushToasts.length > 0 && (
        <div className="rush-toast-stack" aria-live="assertive" aria-atomic="false">
          {rushToasts.map((toast) => (
            <div className="rush-toast" role="alert" key={toast.id}>
              <Icon name="alert" size={32} />
              <div>
                <strong className="rush-toast-title">{toast.title}</strong>
                <p className="rush-toast-detail">{toast.detail}</p>
              </div>
              <button
                className="rush-toast-close"
                type="button"
                aria-label="Dismiss rush alert"
                onClick={() => dismissRushToast(toast.id)}
              >
                <Icon name="close" size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
