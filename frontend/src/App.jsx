import React from 'react'
import AddSourceModal from './components/AddSourceModal'
import Dashboard from './components/Dashboard'
import Icon from './components/Icon'
import Sidebar from './components/Sidebar'
import { createSource, fetchSources, deleteSource, fetchRushAlerts, updateSource } from './services/sourcesApi'

// ---------- Audio alarm (Web Audio API; no asset needed) ----------
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
      gain.gain.exponentialRampToValueAtTime(0.22, startTime + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.32)

      oscillator.connect(gain)
      gain.connect(audioContext.destination)
      oscillator.start(startTime)
      oscillator.stop(startTime + 0.34)
      return oscillator
    }

    // Three-tone alarm pattern (~1.1 s total) — slightly louder than before
    const firstTone = playTone(audioContext.currentTime, 880)
    playTone(audioContext.currentTime + 0.4, 1040)
    playTone(audioContext.currentTime + 0.8, 880)
    firstTone.onended = () => window.setTimeout(() => audioContext.close().catch(() => {}), 1400)
  } catch (error) {
    console.debug('Rush alert sound unavailable:', error)
  }
}

// ---------- Desktop notification (fires even when tab is in background) ----------
function fireDesktopNotification(alert) {
  try {
    if (typeof Notification === 'undefined') return
    if (Notification.permission !== 'granted') return
    const title = `🚨 Rush detected — ${alert.title || alert.camera_id}`
    const body =
      `${alert.current} people · ${Number(alert.ratio).toFixed(2)}× average ` +
      `(z=${Number(alert.z_score).toFixed(2)}) over last ${alert.window_minutes} min`
    const n = new Notification(title, { body, tag: alert.camera_id, requireInteraction: false })
    window.setTimeout(() => n.close(), 12000)
  } catch (error) {
    console.debug('Desktop notification failed:', error)
  }
}

function formatAlertDetail(alert) {
  const current = Number(alert.current) || 0
  const ratio = Number(alert.ratio) || 0
  const windowMinutes = Number(alert.window_minutes) || 10
  return `${current} people · ${ratio.toFixed(2)}× average over last ${windowMinutes} min`
}

export default function App() {
  const [sources, setSources] = React.useState([])
  const [selectedSource, setSelectedSource] = React.useState('')
  const [isAddSourceOpen, setIsAddSourceOpen] = React.useState(false)
  const [isLoadingSources, setIsLoadingSources] = React.useState(true)
  const [sourceLoadError, setSourceLoadError] = React.useState('')
  const [isSavingSource, setIsSavingSource] = React.useState(false)
  const [sourceSaveError, setSourceSaveError] = React.useState('')

  // Active rush state — keyed by camera_id so children can highlight them
  const [activeRushAlerts, setActiveRushAlerts] = React.useState([])
  const [rushToasts, setRushToasts] = React.useState([])
  const activeRushCamerasRef = React.useRef(new Set())
  const lastRushBeepAtRef = React.useRef(0)

  // Derived: Set<camera_id> of cameras currently in rush (passed to Sidebar)
  const activeRushCameraIds = React.useMemo(
    () => new Set(activeRushAlerts.map((a) => a.camera_id)),
    [activeRushAlerts],
  )

  React.useEffect(() => { loadSources() }, [])

  // Request browser notification permission once, on first user gesture
  React.useEffect(() => {
    if (typeof Notification === 'undefined') return
    if (Notification.permission === 'default') {
      const ask = () => {
        Notification.requestPermission().catch(() => {})
        window.removeEventListener('click', ask)
      }
      window.addEventListener('click', ask, { once: true })
      return () => window.removeEventListener('click', ask)
    }
  }, [])

  // Poll rush alerts every 10 seconds for ALL cameras
  React.useEffect(() => {
    let isActive = true

    async function checkRushAlerts() {
      try {
        const alerts = await fetchRushAlerts()
        if (!isActive) return

        const activeAlerts = alerts.filter((alert) => alert.active && alert.status === 'RUSH ALERT')
        const activeCameraIds = new Set(activeAlerts.map((alert) => alert.camera_id))

        // Detect cameras that just entered rush (were NOT in rush last poll)
        const newRushAlerts = activeAlerts.filter(
          (alert) => !activeRushCamerasRef.current.has(alert.camera_id),
        )

        activeRushCamerasRef.current = activeCameraIds
        setActiveRushAlerts(activeAlerts)

        // Audio: beep on any new rush OR every 30 seconds while sustained
        if (activeAlerts.length > 0) {
          const now = Date.now()
          if (newRushAlerts.length > 0 || now - lastRushBeepAtRef.current > 30000) {
            playRushBeep()
            lastRushBeepAtRef.current = now
          }
        }

        // Desktop notification: fire ONCE per camera as it enters rush
        newRushAlerts.forEach((alert) => fireDesktopNotification(alert))

        // Toasts: one per active rush camera
        setRushToasts(
          activeAlerts.map((alert) => ({
            id: alert.camera_id,
            cameraId: alert.camera_id,
            sourceId: alert.source_id,
            title: `Abnormal activity at ${alert.title || alert.camera_id}`,
            detail: formatAlertDetail(alert),
          })),
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

  function jumpToCamera(sourceId) {
    if (sourceId) setSelectedSource(sourceId)
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
        currentSources.map((source) => (source.id === sourceId ? updated : source)),
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
        activeRushCameraIds={activeRushCameraIds}
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

      {/* GLOBAL RUSH BANNER — sticky strip across the top */}
      {activeRushAlerts.length > 0 && (
        <div className="global-rush-banner" role="status" aria-live="polite">
          <Icon name="alert" size={20} />
          <strong>
            {activeRushAlerts.length === 1
              ? '1 camera in active rush'
              : `${activeRushAlerts.length} cameras in active rush`}
          </strong>
          <span className="global-rush-banner-list">
            {activeRushAlerts
              .map((a) => a.title || a.camera_id)
              .join(' · ')}
          </span>
        </div>
      )}

      {/* TOAST STACK — one toast per rush camera */}
      {rushToasts.length > 0 && (
        <div className="rush-toast-stack" aria-live="assertive" aria-atomic="false">
          {rushToasts.map((toast) => (
            <div className="rush-toast" role="alert" key={toast.id}>
              <Icon name="alert" size={32} />
              <div className="rush-toast-body">
                <strong className="rush-toast-title">{toast.title}</strong>
                <p className="rush-toast-detail">{toast.detail}</p>
                {toast.sourceId && toast.sourceId !== selectedSource && (
                  <button
                    className="rush-toast-view"
                    type="button"
                    onClick={() => jumpToCamera(toast.sourceId)}
                  >
                    View this camera →
                  </button>
                )}
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
