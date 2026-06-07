import React from 'react'
import Icon from './Icon'

export default function Sidebar({
  sources,
  selectedSource,
  onSelectSource,
  onAddSource,
  isLoadingSources,
  sourceLoadError,
  onRetryLoad,
  activeRushCameraIds = new Set(),
}) {
  const rushCount = activeRushCameraIds.size
  // Mobile slide-in state. Hamburger button + backdrop live next to the
  // sidebar in the DOM; CSS hides them above 760px so desktop is unchanged.
  const [isMobileOpen, setIsMobileOpen] = React.useState(false)

  const closeMobile = () => setIsMobileOpen(false)

  // Close the panel automatically when the user picks a camera, so they can
  // actually see the dashboard they just selected.
  const handleSelect = (id) => {
    onSelectSource(id)
    closeMobile()
  }

  const handleAdd = () => {
    onAddSource()
    closeMobile()
  }

  // Close on Esc for keyboard users.
  React.useEffect(() => {
    if (!isMobileOpen) return undefined
    const onKey = (event) => { if (event.key === 'Escape') setIsMobileOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isMobileOpen])

  return (
    <>
      <button
        type="button"
        className="sidebar-toggle"
        aria-label={isMobileOpen ? 'Close sidebar' : 'Open sidebar'}
        aria-expanded={isMobileOpen}
        onClick={() => setIsMobileOpen((v) => !v)}
      >
        <Icon name={isMobileOpen ? 'close' : 'menu'} size={22} />
      </button>

      <div
        className={`sidebar-backdrop${isMobileOpen ? ' open' : ''}`}
        onClick={closeMobile}
        aria-hidden="true"
      />

      <aside className={`sidebar${isMobileOpen ? ' open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">CA</div>
          <div>
            <h3>Campus Analytics</h3>
            <p>Mobility & occupancy</p>
          </div>
        </div>

        <button className="add-source" type="button" onClick={handleAdd}>
          <Icon name="plus" />
          <span>Add source</span>
        </button>

        <div className="source-list-header">
          <label className="field-label" htmlFor="source-select">Source</label>
          {rushCount > 0 && (
            <span className="sidebar-rush-summary" title={`${rushCount} camera(s) in active rush`}>
              <span className="rush-dot" />
              {rushCount} in rush
            </span>
          )}
        </div>

        <nav className="source-list" aria-label="Camera sources">
          {isLoadingSources && <p className="source-state">Loading sources...</p>}
          {!isLoadingSources && sourceLoadError && (
            <div className="source-state error">
              <p>{sourceLoadError}</p>
              <button type="button" onClick={onRetryLoad}>
                <Icon name="refresh" />
                <span>Retry</span>
              </button>
            </div>
          )}
          {!isLoadingSources && !sourceLoadError && sources.length === 0 && (
            <p className="source-state">No sources in the database yet.</p>
          )}
          {sources.map((source) => {
            const inRush = activeRushCameraIds.has(source.camera_id)
            const classes = ['source-item']
            if (source.id === selectedSource) classes.push('active')
            if (inRush) classes.push('rush')
            return (
              <button
                key={source.id}
                type="button"
                className={classes.join(' ')}
                onClick={() => handleSelect(source.id)}
                aria-label={inRush ? `${source.title} (in rush)` : source.title}
              >
                <Icon name="camera" />
                <span className="source-item-title">{source.title}</span>
                {inRush && (
                  <span className="rush-badge" title="Active rush alert" aria-hidden="true">
                    <span className="rush-badge-dot" />
                    RUSH
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        <button className="about-button" type="button">
          <Icon name="info" />
          <span>About</span>
        </button>
      </aside>
    </>
  )
}
