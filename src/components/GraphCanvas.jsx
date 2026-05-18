import { ReactFlow, Controls, MiniMap, Background, BackgroundVariant } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

export function GraphCanvas({ nodes, edges, onNodesChange, onEdgesChange, onConnect }) {
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      fitView
      deleteKeyCode="Delete"
    >
      <Controls />
      <MiniMap
        nodeColor="#0071e3"
        maskColor="rgba(0,0,0,0.6)"
        style={{ background: '#2c2c2e' }}
      />
      <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#3a3a3c" />
    </ReactFlow>
  )
}
