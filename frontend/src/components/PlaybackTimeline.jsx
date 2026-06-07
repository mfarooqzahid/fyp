import React from 'react'
import Icon from './Icon'
import {
  getStreamUrl,
  fetchPlaybackTimeline,
  getPlaybackClipUrl,
} from '../services/sourcesApi'

const WINDOW_HOURS = 6

function formatClockTime(unixSeconds) {
  if (!Number.isFinite(unixSeconds)) return '--:--:--'
  const d = new Date(unixSeconds * 1000)
  return d.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatFrameTime(value) {
  if (!value) return 'Waiting'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Waiting'
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// Find the chunk whose [start_ts, end_ts] window contains `ts`. Falls back to
// the chunk with the closest start_ts so the slider always has something to
// resolve to even between chunks.
function findChunkForTs(chunks, ts) {
  if (!Array.isArray(chunks) || chunks.length === 0) return null
  for (const c of chunks) {
    if (ts >= c.start_ts && ts <= c.end_ts) return c
  }
  let best = chunks[0]
  let bestDist = Math.abs(best.start_ts - ts)
  for (const c of chunks) {
    const d = Math.abs(c.start_ts - ts)
    if (d < bestDist) {
      best = c
      bestDist = d
    }
  }
  return best
}

export default function PlaybackTimeline({
  cameraId,
  sourceTitle,
  workerStatus,
  workerAlive,
  lastFrameAt,
}) {
  const [mode, setMode] = React.useState('live') // 'live' | 'playback'
  const [streamNonce, setStreamNonce] = React.useState(Date.now())
  const [streamError, setStreamError] = React.useState(false)
  const [timeline, setTimeline] = React.useState(null) // {chunks, now_iso, ...}
  const [timelineError, setTimelineError] = React.useState(null)
  const [sliderTs, setSliderTs] = React.useState(() => Math.floor(Date.now() / 1000))
  const [activeChunk, setActiveChunk] = React.useState(null)
  const videoRef = React.useRef(null)

  // Reset state on camera change.
  React.useEffect(() => {
    setMode('live')
    setStreamError(false)
    setStreamNonce(Date.now())
    setTimeline(null)
    setTimelineError(null)
    setActiveChunk(null)
    setSliderTs(Math.floor(Date.now() / 1000))
  }, [cameraId])

  // Poll the timeline every 30 s so newly recorded chunks become scrubbable.
  React.useEffect(() => {
    if (!cameraId) return undefined
    let cancelled = false
    const load = async () => {
      try {
        const data = await fetchPlaybackTimeline(cameraId, WINDOW_HOURS)
        if (!cancelled) {
          setTimeline(data)
          setTimelineError(null)
        }
      } catch (err) {
        if (!cancelled) setTimelineError(err.message || String(err))
      }
    }
    load()
    const intervalId = setInterval(load, 30000)
    return () => {
      cancelled = true
      clearInterval(intervalId)
    }
  }, [cameraId])

  const chunks = timeline?.chunks || []
  const now = Math.floor(Date.now() / 1000)
  const sliderMin = now - WINDOW_HOURS * 3600
  const sliderMax = now

  const handleSliderChange = (event) => {
    const value = Number(event.target.value)
    setSliderTs(value)
    const chunk = findChunkForTs(chunks, value)
    if (chunk && (!activeChunk || chunk.start_ts !== activeChunk.start_ts)) {
      setActiveChunk(chunk)
    }
    if (mode !== 'playback') setMode('playback')
  }

  // When the resolved chunk changes, force the video to seek into it. Seeking
  // within the same chunk is handled by adjusting video.currentTime directly
  // without changing the src (avoids a reload).
  React.useEffect(() => {
    if (mode !== 'playback' || !activeChunk || !videoRef.current) return
    const offset = Math.max(0, sliderTs - activeChunk.start_ts)
    try {
      // Setting currentTime only works after metadata has loaded.
      if (Number.isFinite(videoRef.current.duration)) {
        videoRef.current.currentTime = Math.min(offset, videoRef.current.duration)
      }
    } catch (err) {
      // ignore; will retry on next slider change
    }
  }, [mode, activeChunk, sliderTs])

  const onLiveClick = () => {
    setMode('live')
    setStreamError(false)
    setStreamNonce(Date.now())
    setSliderTs(Math.floor(Date.now() / 1000))
  }

  const streamUrl = cameraId ? getStreamUrl(cameraId, streamNonce) : ''
  const clipUrl = activeChunk
    ? getPlaybackClipUrl(cameraId, activeChunk.start_ts)
    : ''

  // Percentage positions for chunk markers on the timeline track.
  const range = sliderMax - sliderMin
  const chunkBlocks = chunks.map((c) => {
    const startPct = Math.max(0, Math.min(100, ((c.start_ts - sliderMin) / range) * 100))
    const widthPct = Math.max(
      0.3,
      Math.min(100 - startPct, ((c.end_ts - c.start_ts) / range) * 100),
    )
    return {
      key: `${c.start_ts}`,
      left: `${startPct}%`,
      width: `${widthPct}%`,
    }
  })

  return (
    <section className="playback-timeline" aria-label="Live & playback viewer">
      <div className="playback-meta">
        <div className="panel-heading">
          <h3>{mode === 'live' ? 'Live Detection' : 'Playback'}</h3>
          <span>
            {mode === 'live'
              ? workerStatus || (workerAlive ? 'running' : 'starting')
              : 'reviewing past footage'}
          </span>
        </div>
        <dl>
          <div><dt>Source</dt><dd>{sourceTitle || cameraId}</dd></div>
          <div><dt>Camera</dt><dd>{cameraId}</dd></div>
          <div>
            <dt>{mode === 'live' ? 'Last frame' : 'Playing'}</dt>
            <dd>
              {mode === 'live'
                ? formatFrameTime(lastFrameAt)
                : formatClockTime(sliderTs)}
            </dd>
          </div>
        </dl>
      </div>

      <div className="playback-viewport">
        {mode === 'live' ? (
          !streamError ? (
            <img
              key={streamNonce}
              src={streamUrl}
              alt={`${sourceTitle || cameraId} live YOLO detection stream`}
              onLoad={() => setStreamError(false)}
              onError={() => setStreamError(true)}
            />
          ) : (
            <div className="playback-empty">Waiting for detection stream</div>
          )
        ) : clipUrl ? (
          <video
            ref={videoRef}
            key={clipUrl}
            src={clipUrl}
            controls
            autoPlay
            muted
            playsInline
          />
        ) : (
          <div className="playback-empty">No recorded footage in this window</div>
        )}
      </div>

      <div className="playback-controls">
        <button
          type="button"
          className={`playback-live-btn${mode === 'live' ? ' active' : ''}`}
          onClick={onLiveClick}
          aria-label="Return to live stream"
        >
          <span className="playback-live-dot" />
          LIVE
        </button>
        <div className="playback-timeline-track">
          <div className="playback-timeline-chunks" aria-hidden="true">
            {chunkBlocks.map((b) => (
              <span key={b.key} style={{ left: b.left, width: b.width }} />
            ))}
          </div>
          <input
            type="range"
            min={sliderMin}
            max={sliderMax}
            step={1}
            value={sliderTs}
            onChange={handleSliderChange}
            aria-label="Scrub recorded footage"
          />
          <div className="playback-timeline-labels" aria-hidden="true">
            <span>{formatClockTime(sliderMin)}</span>
            <span>{formatClockTime(sliderMin + range / 2)}</span>
            <span>{formatClockTime(sliderMax)}</span>
          </div>
        </div>
        <div className="playback-time-readout">
          {mode === 'live' ? 'LIVE' : formatClockTime(sliderTs)}
        </div>
      </div>

      {timelineError && (
        <div className="playback-error">Timeline unavailable: {timelineError}</div>
      )}
      {!timelineError && mode === 'playback' && chunks.length === 0 && (
        <div className="playback-error">
          No recorded chunks yet. Recording starts when the camera worker is running.
        </div>
      )}
    </section>
  )
}
