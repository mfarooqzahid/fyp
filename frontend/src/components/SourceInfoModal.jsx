import React from 'react'
import Icon from './Icon'

export default function SourceInfoModal({ source, onClose, onDelete, onUpdate }) {
  const [isEditing, setIsEditing] = React.useState(false)
  const [form, setForm] = React.useState({
    title: '',
    description: '',
    mode: 'generate',
    streamUrl: '',
  })
  const [errors, setErrors] = React.useState({})
  const [isSaving, setIsSaving] = React.useState(false)
  const [serverError, setServerError] = React.useState('')

  React.useEffect(() => {
    if (source) {
      setForm({
        title: source.title || '',
        description: source.description || '',
        mode: source.mode || 'generate',
        streamUrl: source.streamUrl || '',
      })
    }
  }, [source])

  React.useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!source) {
    return null
  }

  const sourceType = source.mode === 'stream' ? 'Stream' : 'Generated'
  const streamStatus = source.worker_status || (source.worker_alive ? 'running' : 'stopped')

  function updateField(field, value) {
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
    setErrors((currentErrors) => ({ ...currentErrors, [field]: '' }))
  }

  function toggleGenerateMode() {
    setForm((currentForm) => ({
      ...currentForm,
      mode: currentForm.mode === 'generate' ? 'stream' : 'generate',
    }))
    setErrors((currentErrors) => ({ ...currentErrors, streamUrl: '' }))
  }

  function validateForm() {
    const nextErrors = {}

    if (!form.title.trim()) {
      nextErrors.title = 'Title is required.'
    }

    if (!form.description.trim()) {
      nextErrors.description = 'Description is required.'
    }

    if (form.mode === 'stream') {
      if (!form.streamUrl.trim()) {
        nextErrors.streamUrl = 'Stream URL is required.'
      } else {
        try {
          const url = new URL(form.streamUrl)
          const validProtocol = ['http:', 'https:', 'rtsp:'].includes(url.protocol)

          if (!validProtocol) {
            nextErrors.streamUrl = 'Use a valid http, https, or rtsp URL.'
          }
        } catch {
          nextErrors.streamUrl = 'Enter a valid stream URL.'
        }
      }
    }

    return nextErrors
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!onUpdate) return

    const nextErrors = validateForm()
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setIsSaving(true)
    setServerError('')

    try {
      await onUpdate(source.id, form)
      setIsEditing(false)
    } catch (err) {
      setServerError(err.message || 'Failed to update camera source.')
    } finally {
      setIsSaving(false)
    }
  }

  const Container = isEditing ? 'form' : 'section'

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <Container
        className="source-info-dialog"
        role={isEditing ? undefined : "dialog"}
        aria-modal={isEditing ? undefined : "true"}
        aria-labelledby="source-info-title"
        onSubmit={isEditing ? handleSubmit : undefined}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <h2 id="source-info-title">{isEditing ? 'Edit Source' : 'Source Details'}</h2>
          <button className="dialog-close" type="button" aria-label="Close" onClick={onClose} disabled={isSaving}>
            <Icon name="close" />
          </button>
        </div>

        {serverError && <p className="server-error">{serverError}</p>}

        {isEditing ? (
          <div className="source-details-edit" style={{ display: 'grid', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontWeight: '800', fontSize: '13px', color: '#667085', textTransform: 'uppercase' }}>Title</label>
              <input
                className={errors.title ? 'dialog-input field-error' : 'dialog-input'}
                type="text"
                value={form.title}
                onChange={(event) => updateField('title', event.target.value)}
                autoFocus
                aria-invalid={Boolean(errors.title)}
              />
              {errors.title && <p className="error-message" style={{ marginTop: '4px' }}>{errors.title}</p>}
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontWeight: '800', fontSize: '13px', color: '#667085', textTransform: 'uppercase' }}>Description</label>
              <textarea
                className={errors.description ? 'dialog-textarea field-error' : 'dialog-textarea'}
                style={{ minHeight: '100px' }}
                value={form.description}
                onChange={(event) => updateField('description', event.target.value)}
                aria-invalid={Boolean(errors.description)}
              />
              {errors.description && <p className="error-message" style={{ marginTop: '4px' }}>{errors.description}</p>}
            </div>

            <div className="stream-url-field">
              <div className="stream-url-header">
                <label htmlFor="stream-url">Stream URL</label>
                <button
                  type="button"
                  className={form.mode === 'generate' ? 'generate-toggle active' : 'generate-toggle'}
                  aria-pressed={form.mode === 'generate'}
                  onClick={toggleGenerateMode}
                >
                  <span className="generate-toggle-track" aria-hidden="true">
                    <span className="generate-toggle-thumb" />
                  </span>
                  <span>Generate Data</span>
                </button>
              </div>
              <input
                id="stream-url"
                className={errors.streamUrl ? 'dialog-input field-error' : 'dialog-input'}
                type="url"
                placeholder="stream url"
                value={form.streamUrl}
                onChange={(event) => updateField('streamUrl', event.target.value)}
                disabled={form.mode === 'generate'}
                aria-invalid={Boolean(errors.streamUrl)}
              />
            </div>
            {form.mode === 'stream' && errors.streamUrl && (
              <p className="error-message" style={{ marginTop: '4px' }}>{errors.streamUrl}</p>
            )}
          </div>
        ) : (
          <dl className="source-details">
            <div>
              <dt>Title</dt>
              <dd>{source.title}</dd>
            </div>
            <div>
              <dt>Description</dt>
              <dd>{source.description || 'No description provided.'}</dd>
            </div>
            <div>
              <dt>Source Type</dt>
              <dd>{sourceType}</dd>
            </div>
            {source.mode === 'stream' && (
              <>
                <div>
                  <dt>Stream URL</dt>
                  <dd>{source.streamUrl || 'No stream URL provided.'}</dd>
                </div>
                <div>
                  <dt>Stream Status</dt>
                  <dd>{streamStatus}</dd>
                </div>
                <div>
                  <dt>Last Frame</dt>
                  <dd>{source.last_frame_at || 'No frame received yet.'}</dd>
                </div>
                {source.last_error && (
                  <div>
                    <dt>Last Error</dt>
                    <dd>{source.last_error}</dd>
                  </div>
                )}
              </>
            )}
          </dl>
        )}

        <div className="dialog-footer">
          {isEditing ? (
            <>
              <button
                className="confirm-source"
                type="submit"
                disabled={isSaving}
              >
                <Icon name="check" />
                <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
              </button>
              <button
                className="cancel-source-button"
                type="button"
                onClick={() => {
                  setIsEditing(false)
                  setForm({
                    title: source.title || '',
                    description: source.description || '',
                    mode: source.mode || 'generate',
                    streamUrl: source.streamUrl || '',
                  })
                  setErrors({})
                  setServerError('')
                }}
                disabled={isSaving}
              >
                <span>Cancel</span>
              </button>
            </>
          ) : (
            <>
              {onUpdate && (
                <button
                  className="edit-source-button"
                  type="button"
                  onClick={() => setIsEditing(true)}
                >
                  <Icon name="edit" />
                  <span>Edit Source</span>
                </button>
              )}
              {onDelete && (
                <button
                  className="delete-source-button"
                  type="button"
                  onClick={() => {
                    if (window.confirm(`Are you sure you want to delete "${source.title}"? This will stop any running simulation and remove all log history.`)) {
                      onDelete(source.id)
                    }
                  }}
                >
                  <Icon name="trash" />
                  <span>Delete Source</span>
                </button>
              )}
            </>
          )}
        </div>
      </Container>
    </div>
  )
}
