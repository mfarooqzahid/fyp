import React from 'react'
import AddSourceModal from './components/AddSourceModal'
import Dashboard from './components/Dashboard'
import Sidebar from './components/Sidebar'
import { createSource, fetchSources, deleteSource, updateSource } from './services/sourcesApi'

export default function App() {
  const [sources, setSources] = React.useState([])
  const [selectedSource, setSelectedSource] = React.useState('')
  const [isAddSourceOpen, setIsAddSourceOpen] = React.useState(false)
  const [isLoadingSources, setIsLoadingSources] = React.useState(true)
  const [sourceLoadError, setSourceLoadError] = React.useState('')
  const [isSavingSource, setIsSavingSource] = React.useState(false)
  const [sourceSaveError, setSourceSaveError] = React.useState('')

  React.useEffect(() => {
    loadSources()
  }, [])

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
    </div>
  )
}
