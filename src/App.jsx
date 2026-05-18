import { useState, useCallback } from 'react'
import { ReactFlowProvider, useNodesState, useEdgesState, addEdge } from '@xyflow/react'
import { GraphCanvas } from './components/GraphCanvas'
import './App.css'

let nodeCounter = 1

function AppInner() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [projectName, setProjectName] = useState('Мій проект')
  const [status, setStatus] = useState('')

  const onConnect = useCallback(
    (connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  )

  const addNode = () => {
    const id = `node-${Date.now()}`
    setNodes((nds) => [
      ...nds,
      {
        id,
        position: { x: Math.random() * 500 + 100, y: Math.random() * 350 + 80 },
        data: { label: `Об'єкт ${nodeCounter++}` }
      }
    ])
  }

  const showStatus = (msg) => {
    setStatus(msg)
    setTimeout(() => setStatus(''), 2500)
  }

  const handleSave = async () => {
    await window.api.saveProject(projectName, { nodes, edges })
    showStatus('Збережено')
  }

  const handleLoad = async () => {
    const data = await window.api.loadProject(projectName)
    if (data) {
      setNodes(data.nodes || [])
      setEdges(data.edges || [])
      showStatus('Завантажено')
    } else {
      showStatus('Файл не знайдено')
    }
  }

  return (
    <div className="app">
      <header className="toolbar">
        <span className="app-title">Analyst's Notebook</span>
        <input
          className="project-name"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="Назва проекту"
        />
        <button className="primary" onClick={addNode}>+ Вузол</button>
        <button onClick={handleSave}>Зберегти</button>
        <button onClick={handleLoad}>Відкрити</button>
        {status && <span className="status">{status}</span>}
      </header>
      <div className="canvas-wrap">
        <GraphCanvas
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
        />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppInner />
    </ReactFlowProvider>
  )
}
