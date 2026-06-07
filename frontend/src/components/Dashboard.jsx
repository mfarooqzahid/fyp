import React from 'react'
import ReactECharts from 'echarts-for-react'
import Icon from './Icon'
import SourceInfoModal from './SourceInfoModal'
import PlaybackTimeline from './PlaybackTimeline'
import { fetchDashboardData } from '../services/sourcesApi'

function formatNumber(value) {
  return new Intl.NumberFormat('en').format(Number(value) || 0)
}

function formatTrendLabel(direction, change) {
  const prefix = direction === 'up' ? 'Up' : direction === 'down' ? 'Down' : 'Same'
  return `${prefix} ${Math.abs(Number(change) || 0)}%`
}

function congestionClass(status) {
  if (status === 'HIGH') return 'high'
  if (status === 'MEDIUM') return 'medium'
  return 'low'
}

export default function Dashboard({ sources, selectedSource, onDeleteSource, onUpdateSource }) {
  const currentSource = sources.find((source) => source.id === selectedSource)
  const cameraNameById = React.useMemo(() => {
    return sources.reduce((lookup, source) => {
      if (source.camera_id) {
        lookup[source.camera_id] = source.title || source.camera_id
      }
      return lookup
    }, {})
  }, [sources])
  const [isInfoOpen, setIsInfoOpen] = React.useState(false)
  const [dashboardData, setDashboardData] = React.useState(null)
  const [loadedCameraId, setLoadedCameraId] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [isSourceLoading, setIsSourceLoading] = React.useState(false)
  const [error, setError] = React.useState(null)
  const [failedCameraId, setFailedCameraId] = React.useState('')
  const [refreshTrigger, setRefreshTrigger] = React.useState(0)
  const currentCameraId = currentSource?.camera_id || ''
  const isStreamSource = currentSource?.mode === 'stream' || currentSource?.mode === 'live'
  const showDetectionPreview = Boolean(isStreamSource && currentCameraId)
  const hasCurrentDashboardData = Boolean(dashboardData && loadedCameraId === currentCameraId)
  const hasCurrentError = Boolean(error && failedCameraId === currentCameraId)
  const showDashboardLoading = Boolean(currentCameraId && !hasCurrentDashboardData && !hasCurrentError)

  React.useEffect(() => {
    if (!currentCameraId) {
      setDashboardData(null)
      setLoadedCameraId('')
      setLoading(false)
      setIsSourceLoading(false)
      setError(null)
      setFailedCameraId('')
      return
    }

    let isActive = true

    setDashboardData(null)
    setLoadedCameraId('')
    setError(null)
    setFailedCameraId('')
    setIsSourceLoading(true)

    const fetchData = async (isInitialLoad = false) => {
      try {
        setLoading(true)
        const data = await fetchDashboardData(currentCameraId, currentSource?.mode)
        if (!isActive) return
        setDashboardData(data)
        setLoadedCameraId(currentCameraId)
        setError(null)
        setFailedCameraId('')
      } catch (err) {
        if (!isActive) return
        console.error('Failed to fetch dashboard data:', err)
        setError(err.message)
        setFailedCameraId(currentCameraId)
      } finally {
        if (isActive) {
          setLoading(false)
          if (isInitialLoad) setIsSourceLoading(false)
        }
      }
    }

    fetchData(true)
    const interval = setInterval(fetchData, 10000)

    return () => {
      isActive = false
      clearInterval(interval)
    }
  }, [currentCameraId, currentSource?.mode, refreshTrigger])

  const liveTrend = Array.isArray(dashboardData?.live_trend) ? dashboardData.live_trend : []
  const trendLabels = liveTrend.map((point) => Array.isArray(point) ? point[0] : '')
  const trendValues = liveTrend.map((point) => Array.isArray(point) ? Number(point[1]) || 0 : 0)
  const hasTrendData = hasCurrentDashboardData && trendValues.length > 0
  const flow = dashboardData?.flow || {}
  const rushAlert = dashboardData?.rush_alert || {}
  const dailySummary = dashboardData?.daily_summary || {}
  const peakHours = Array.isArray(dashboardData?.peak_hours) ? dashboardData.peak_hours : []
  const gateComparison = Array.isArray(dashboardData?.gate_comparison) ? dashboardData.gate_comparison : []
  const congestion = Array.isArray(dashboardData?.congestion) ? dashboardData.congestion : []
  const weekOverWeek = dashboardData?.week_over_week || {}
  const waitMetric = dashboardData?.average_wait_time || dashboardData?.metric_availability?.average_wait_time
  const getCameraName = (cameraId) => cameraNameById[cameraId] || cameraId

  const emptyMetricState = currentCameraId ? 'Loading' : 'No source'
  const displayMetrics = hasCurrentDashboardData
    ? [
        { label: 'Current Occupancy', value: dashboardData.occupancy ?? 0, delta: dashboardData.occupancy_details?.scope || 'gate', icon: 'users', iconClass: 'icon-occupancy' },
        { label: 'Incoming', value: dashboardData.entries ?? 0, delta: `${flow.incoming_percent ?? 0}% of flow`, icon: 'arrowDown', iconClass: 'icon-incoming' },
        { label: 'Outgoing', value: dashboardData.exits ?? 0, delta: `${flow.outgoing_percent ?? 0}% of flow`, icon: 'arrowUp', iconClass: 'icon-outgoing' },
        { label: 'Rush Status', value: rushAlert.status || 'NORMAL', delta: `${rushAlert.window_minutes || 10} min window`, icon: 'alert', iconClass: 'icon-rush' },
      ]
    : [
        { label: 'Current Occupancy', value: 0, delta: emptyMetricState, icon: 'users', iconClass: 'icon-occupancy' },
        { label: 'Incoming', value: 0, delta: emptyMetricState, icon: 'arrowDown', iconClass: 'icon-incoming' },
        { label: 'Outgoing', value: 0, delta: emptyMetricState, icon: 'arrowUp', iconClass: 'icon-outgoing' },
        { label: 'Rush Status', value: 'N/A', delta: emptyMetricState, icon: 'alert', iconClass: 'icon-rush' },
      ]
  // Render skeleton placeholders while we're waiting for the very first
  // payload for the selected camera, so the user gets a clear loading cue
  // instead of stale zeros.
  const isMetricsLoading = showDashboardLoading

  // Larger, bolder axis labels for readability during projector demos.
  const axisLabelStyle = { color: '#475467', fontSize: 13, fontWeight: 700 }
  const tooltipStyle = {
    textStyle: { fontSize: 13, fontWeight: 600 },
    backgroundColor: '#ffffff',
    borderColor: '#d8e1ea',
    borderWidth: 1,
    extraCssText: 'box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12); border-radius: 8px;',
  }

  const axisNameStyle = { color: '#172033', fontSize: 13, fontWeight: 800 }
  const valueLabelStyle = {
    show: true,
    color: '#172033',
    fontSize: 11,
    fontWeight: 800,
    backgroundColor: 'rgba(255, 255, 255, 0.85)',
    padding: [2, 4],
    borderRadius: 3,
  }

  const occupancyTrendOption = {
    tooltip: {
      trigger: 'axis',
      ...tooltipStyle,
      formatter: (params) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const p = params[0]
        return `<strong>${p.axisValue}</strong><br/>${p.marker} Occupancy: <strong>${p.value} people</strong>`
      },
    },
    grid: { top: 40, right: 28, bottom: 56, left: 62 },
    xAxis: {
      type: 'category',
      name: 'Time (HH:MM)',
      nameLocation: 'middle',
      nameGap: 32,
      nameTextStyle: axisNameStyle,
      boundaryGap: false,
      data: trendLabels,
      axisLine: { lineStyle: { color: '#d9e1ea' } },
      axisTick: { show: false },
      axisLabel: axisLabelStyle,
    },
    yAxis: {
      type: 'value',
      name: 'People in area',
      nameLocation: 'middle',
      nameGap: 44,
      nameTextStyle: axisNameStyle,
      splitLine: { lineStyle: { color: '#edf2f7' } },
      axisLabel: { ...axisLabelStyle, formatter: '{value}' },
      minInterval: 1,
    },
    series: [
      {
        name: 'Occupancy',
        type: 'line',
        smooth: true,
        data: trendValues,
        symbolSize: 8,
        // Value label on each data point so the user doesn't have to hover or
        // guess. Only show when the dataset is small enough to stay readable.
        label: trendValues.length <= 24 ? valueLabelStyle : { show: false },
        lineStyle: { width: 4, color: '#2563eb' },
        itemStyle: { color: '#2563eb' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37, 99, 235, 0.28)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
            ],
          },
        },
      },
    ],
  }

  const gateComparisonOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...tooltipStyle,
      formatter: (params) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const p = params[0]
        return `<strong>${p.name}</strong><br/>${p.marker} Total traffic: <strong>${p.value} people</strong>`
      },
    },
    grid: { top: 40, right: 28, bottom: 60, left: 70 },
    xAxis: {
      type: 'category',
      name: 'Camera / Gate',
      nameLocation: 'middle',
      nameGap: 36,
      nameTextStyle: axisNameStyle,
      data: gateComparison.map((gate) => getCameraName(gate.camera)),
      axisTick: { show: false },
      axisLabel: { ...axisLabelStyle, interval: 0, rotate: gateComparison.length > 4 ? 20 : 0 },
    },
    yAxis: {
      type: 'value',
      name: 'Total traffic (people)',
      nameLocation: 'middle',
      nameGap: 48,
      nameTextStyle: axisNameStyle,
      splitLine: { lineStyle: { color: '#edf2f7' } },
      axisLabel: axisLabelStyle,
      minInterval: 1,
    },
    series: [
      {
        name: 'Traffic',
        type: 'bar',
        data: gateComparison.map((gate) => gate.traffic),
        itemStyle: { color: '#0f766e', borderRadius: [6, 6, 0, 0] },
        barMaxWidth: 48,
        // Show value on top of each bar so the user reads numbers directly.
        label: {
          show: true,
          position: 'top',
          color: '#0f766e',
          fontSize: 12,
          fontWeight: 800,
          formatter: '{c}',
        },
      },
    ],
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <h2>
            {currentSource?.title || 'Camera'}
            <button
              className="source-info-button"
              type="button"
              aria-label="Show source details"
              onClick={() => setIsInfoOpen(true)}
            >
              <Icon name="info" size={20} />
            </button>
            <button
              className="source-info-button"
              type="button"
              aria-label="Refresh analytics data"
              onClick={() => setRefreshTrigger((prev) => prev + 1)}
              style={{ marginLeft: '8px' }}
            >
              <Icon name="refresh" size={20} />
            </button>
          </h2>
          <p>{currentSource ? `${currentSource.title} overview` : 'No source selected'}</p>
        </div>
        <div className="live-pill">
          <Icon name="activity" />
          <span>{loading ? 'Updating...' : 'Live monitoring'}</span>
        </div>
      </header>

      <section className="metrics" aria-label="Camera metrics">
        {displayMetrics.map((metric) => (
          <article
            className={`metric-card${isMetricsLoading ? ' is-skeleton' : ''}`}
            key={metric.label}
          >
            <div className="metric-header">
              <p>{metric.label}</p>
              <span className={`metric-icon ${metric.iconClass || ''}`} aria-hidden="true">
                <Icon name={metric.icon || 'activity'} size={18} />
              </span>
            </div>
            {isMetricsLoading ? (
              <>
                <span className="metric-skel-value skeleton" />
                <span className="metric-skel-delta skeleton" />
              </>
            ) : (
              <>
                <strong>{typeof metric.value === 'number' ? formatNumber(metric.value) : metric.value}</strong>
                <span>{metric.delta}</span>
              </>
            )}
          </article>
        ))}
      </section>

      <section className="dashboard-grid" aria-label="Operational metrics">
        <article className="flow-panel">
          <div className="panel-heading">
            <h3>Incoming vs Outgoing Flow</h3>
            <span>{formatNumber(flow.total)} total movements</span>
          </div>
          <div className="flow-bars">
            <div>
              <div className="flow-label">
                <span>Incoming</span>
                <strong>{flow.incoming_percent ?? 0}%</strong>
              </div>
              <div className="meter"><span style={{ width: `${flow.incoming_percent ?? 0}%` }} /></div>
            </div>
            <div>
              <div className="flow-label">
                <span>Outgoing</span>
                <strong>{flow.outgoing_percent ?? 0}%</strong>
              </div>
              <div className="meter outgoing"><span style={{ width: `${flow.outgoing_percent ?? 0}%` }} /></div>
            </div>
          </div>
        </article>

        <article className={rushAlert.active ? 'rush-panel active' : 'rush-panel'}>
          <div className="panel-heading">
            <h3>Crowd Surge Monitor</h3>
            <span>{rushAlert.status || 'NORMAL'}</span>
          </div>
          <strong>{formatNumber(rushAlert.current)} people</strong>
          <p>{rushAlert.ratio ? `${rushAlert.ratio}x average in the last ${rushAlert.window_minutes} minutes` : 'Waiting for enough movement history'}</p>
        </article>

        <article className="peak-panel">
          <div className="panel-heading">
            <h3>Peak Hours Today</h3>
            <span>Top traffic slots</span>
          </div>
          <div className="peak-list">
            {peakHours.length > 0 ? peakHours.map((slot, index) => (
              <div className="peak-row" key={`${slot.time}-${index}`}>
                <span>{slot.time}</span>
                <strong>{formatNumber(slot.count)} people</strong>
              </div>
            )) : (
              <div className="empty-inline">No peak data yet</div>
            )}
          </div>
        </article>
      </section>

      <section className="chart-layout">
        <article className="chart-panel">
          <div className="panel-heading">
            <h3>Hourly Trend Graph</h3>
            <span>Live occupancy</span>
          </div>
          {hasTrendData ? (
            <ReactECharts option={occupancyTrendOption} style={{ height: '100%', minHeight: 260 }} />
          ) : (
            <div className="chart-empty-state">No occupancy trend data yet</div>
          )}
        </article>

        <article className="chart-panel">
          <div className="panel-heading">
            <h3>Gate Comparison</h3>
            <span>Traffic share</span>
          </div>
          {gateComparison.length > 0 ? (
            <ReactECharts option={gateComparisonOption} style={{ height: '100%', minHeight: 260 }} />
          ) : (
            <div className="chart-empty-state">No gate comparison data yet</div>
          )}
        </article>
      </section>

      <section className="status-grid" aria-label="Summary metrics">
        <article className="summary-panel">
          <div className="panel-heading">
            <h3>Daily Traffic Summary</h3>
            <span>{dailySummary.date || 'Today'}</span>
          </div>
          <dl className="summary-list">
            <div><dt>Total entries</dt><dd>{formatNumber(dailySummary.total_entries)}</dd></div>
            <div><dt>Total exits</dt><dd>{formatNumber(dailySummary.total_exits)}</dd></div>
            <div><dt>Peak count</dt><dd>{formatNumber(dailySummary.peak_count)}</dd></div>
            <div><dt>Rush events</dt><dd>{formatNumber(dailySummary.rush_events)}</dd></div>
          </dl>
        </article>

        <article className="summary-panel">
          <div className="panel-heading">
            <h3>Congestion Level</h3>
            <span>Current vs historical max</span>
          </div>
          <div className="congestion-list">
            {congestion.length > 0 ? congestion.map((gate) => (
              <div className="congestion-row" key={gate.camera}>
                <span className={`status-dot ${congestionClass(gate.status)}`} />
                <span>{getCameraName(gate.camera)}</span>
                <strong>{gate.status} ({gate.percent}%)</strong>
              </div>
            )) : (
              <div className="empty-inline">No congestion data yet</div>
            )}
          </div>
        </article>

        <article className="summary-panel">
          <div className="panel-heading">
            <h3>Week-over-Week</h3>
            <span>{formatTrendLabel(weekOverWeek.direction, weekOverWeek.change_percent)}</span>
          </div>
          <dl className="summary-list">
            <div><dt>This week</dt><dd>{formatNumber(weekOverWeek.current_total)}</dd></div>
            <div><dt>Last week</dt><dd>{formatNumber(weekOverWeek.previous_total)}</dd></div>
            <div><dt>Change</dt><dd>{formatTrendLabel(weekOverWeek.direction, weekOverWeek.change_percent)}</dd></div>
          </dl>
        </article>

        <article className="summary-panel muted">
          <div className="panel-heading">
            <h3>Average Crossing Time</h3>
            <span>{waitMetric?.label || 'Unavailable'}</span>
          </div>
          <p>{waitMetric?.reason || 'Requires track lifecycle timestamps before this metric can be calculated.'}</p>
        </article>
      </section>

      {showDetectionPreview && (
        <PlaybackTimeline
          cameraId={currentCameraId}
          sourceTitle={currentSource?.title}
          workerStatus={currentSource?.worker_status}
          workerAlive={currentSource?.worker_alive}
          lastFrameAt={currentSource?.last_frame_at}
        />
      )}

      {isInfoOpen && (
        <SourceInfoModal
          source={currentSource}
          onClose={() => setIsInfoOpen(false)}
          onDelete={(sourceId) => {
            setIsInfoOpen(false)
            onDeleteSource(sourceId)
          }}
          onUpdate={onUpdateSource}
        />
      )}
      {showDashboardLoading && (
        <div className='dashboard-loading-overlay' role='status' aria-live='polite'>
          <div className='dashboard-loading-card'>{isSourceLoading ? 'Loading camera data...' : 'Refreshing camera data...'}</div>
        </div>
      )}
      {hasCurrentError && (
        <div className="dashboard-error">
          Error: {error}
        </div>
      )}
    </main>
  )
}
