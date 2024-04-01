"use client";

import React, { useMemo, useRef, useEffect, useState } from "react";
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import 'reactflow/dist/style.css';

import type {
  Edge,
  Node,
  NodeProps
} from "reactflow";

import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState
} from "reactflow";

export const Editor = () => {
  const monacoEl = useRef(null);
  const editor = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);

  useEffect(() => {
    if (monacoEl.current && editor.current === null) {
      const newEditor = monaco.editor.create(monacoEl.current, {
        value: ['function x() {', '\tconsole.log("Hello world!");', '}'].join('\n'),
        language: 'typescript',
      });
      editor.current = newEditor;
    }

    return () => {
      if (editor.current) {
        editor.current.dispose();
        editor.current = null;
      }
    };
  }, [monacoEl.current]);

  return <div className="w-full h-full" ref={monacoEl}></div>;
};

interface ParadiseEdge {
  src: string;
  src_clock: number;

  message_type: string;

  dst: string;
  dst_handler: string;
  dst_clock: number;
}

interface ParadiseSnapshot {
  nodes: number[];
  edges: ParadiseEdge[];
}

const EventNode = (props: NodeProps): JSX.Element => {
  return (
    <div className="event-node">
      {/* Duplicate top and bottom so that every node can send/receive from either top/bottom */}
      <Handle
        id={`${props.id}-top-target`}
        type="target"
        position={Position.Top}
      />
      <Handle
        id={`${props.id}-top-source`}
        type="source"
        position={Position.Top}
      />

      <Handle id={`${props.id}-left`} type="target" position={Position.Left} />
      <Handle
        id={`${props.id}-right`}
        type="source"
        position={Position.Right}
      />

      <Handle
        id={`${props.id}-bottom-target`}
        type="target"
        position={Position.Bottom}
      />
      <Handle
        id={`${props.id}-bottom-source`}
        type="source"
        position={Position.Bottom}
      />
      {/* <div>{props.data.label}</div> */}
    </div>
  );
};

const snapshotString = `{"nodes": [0, 1, 2], "edges": [{"src": "2", "src_clock": 0, "message_type": "Petition", "dst": "0", "dst_handler": "handle_petition", "dst_clock": 1}, {"src": "0", "src_clock": 1, "message_type": "Vote", "dst": "2", "dst_handler": "handle_vote", "dst_clock": 2}, {"src": "1", "src_clock": 0, "message_type": "Petition", "dst": "2", "dst_handler": "handle_petition", "dst_clock": 3}, {"src": "0", "src_clock": 0, "message_type": "Petition", "dst": "1", "dst_handler": "handle_petition", "dst_clock": 4}, {"src": "2", "src_clock": 3, "message_type": "Vote", "dst": "1", "dst_handler": "handle_vote", "dst_clock": 5}, {"src": "1", "src_clock": 4, "message_type": "Vote", "dst": "0", "dst_handler": "handle_vote", "dst_clock": 6}]}`;

const snapshot = JSON.parse(snapshotString) as ParadiseSnapshot;

function Visualizer() {
  const nodeTypes = useMemo(() => ({ eventNode: EventNode }), []);

  const initialParadiseEdges = (nodes: Record<string, Node[]>): Edge[] => {
    // There are two types of edges:
    //  1. TimelineSegment
    //  2. Message
    //
    // TimelineSegment edges connect events that happen on the same
    // node so that they visually appear on the same horizontal line.

    const timelineSegments: Edge[] = [];

    for (const machineID in nodes) {
      const machineNodes = nodes[machineID];

      for (let i = 0; i < machineNodes.length - 1; i++) {
        const node = machineNodes[i];
        const nextNode = machineNodes[i + 1];

        timelineSegments.push({
          id: `${node.id}-${nextNode.id}`,
          source: node.id,
          target: nextNode.id,
          type: "straight",
          sourceHandle: `${node.id}-right`,
          targetHandle: `${nextNode.id}-left`,
        });
      }
    }

    const verticalIndex = (id: string) =>
      snapshot.nodes.map((n) => n.toString()).indexOf(id);

    const messageEdges = snapshot.edges.map((edge) => {
      const sourceVerticalIndex = verticalIndex(edge.src);
      const destVerticalIndex = verticalIndex(edge.dst);

      const sourceHandle =
        sourceVerticalIndex < destVerticalIndex
          ? `${edge.src}-${edge.src_clock}-bottom-source`
          : `${edge.src}-${edge.src_clock}-top-source`;
      const targetHandle =
        sourceVerticalIndex < destVerticalIndex
          ? `${edge.dst}-${edge.dst_clock}-top-target`
          : `${edge.dst}-${edge.dst_clock}-bottom-target`;

      const color = edge.message_type == "Petition" ? "blue" : "orange";

      return {
        id: `${edge.src}-${edge.src_clock}-${edge.dst}-${edge.dst_clock}`,
        label: edge.message_type,
        source: `${edge.src}-${edge.src_clock}`,
        sourceHandle,
        target: `${edge.dst}-${edge.dst_clock}`,
        targetHandle,
        type: "straight",
        animated: true,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 10,
          height: 10,
          color,
        },
        style: {
          strokeWidth: 2,
          stroke: color,
        },
      };
    });

    return [...timelineSegments, ...messageEdges];
  };

  const getMachineIDToGraphNodeMapping = (): Record<string, Node[]> => {
    // Mapping from machine node ID to list of the graph nodes
    const machineToGraphNodeMapping: Record<string, Node[]> = {};

    const addToMapping = (id: string, node: Node) => {
      if (!machineToGraphNodeMapping[id]) {
        machineToGraphNodeMapping[id] = [];
      }
      machineToGraphNodeMapping[id].push(node);
    };

    snapshot.edges.forEach((edge: ParadiseEdge) => {
      const newNodes: Node[] = [];

      const verticalIndex = (id: string) =>
        snapshot.nodes.map((n) => n.toString()).indexOf(id);

      // If the source timestamp is a 0, then it is being initialized. Otherwise,
      if (edge.src_clock === 0) {
        const initNode: Node = {
          id: `${edge.src}-${edge.src_clock}`,
          position: {
            x: edge.src_clock * 100,
            y: verticalIndex(edge.src) * 100,
          },
          data: {
            label: `Init: Node: ${edge.src}, Clock: ${edge.src_clock}`,
            clock: edge.src_clock,
          },
          sourcePosition: Position.Right,
          type: "eventNode",
        };

        addToMapping(edge.src, initNode);
      }

      const destNode: Node = {
        id: `${edge.dst}-${edge.dst_clock}`,
        position: { x: edge.dst_clock * 100, y: verticalIndex(edge.dst) * 100 },
        data: {
          label: `${edge.dst_handler}: Node: ${edge.dst}, Clock: ${edge.dst_clock}`,
          clock: edge.dst_clock,
        },
        targetPosition: Position.Left,
        sourcePosition: Position.Right,
        type: "eventNode",
      };
      addToMapping(edge.dst, destNode);
    });

    // Sort each value array in-place based on data.clock
    Object.values(machineToGraphNodeMapping).forEach((nodes: Node[]) =>
      nodes.sort((a, b) => a.data.clock - b.data.clock)
    );

    return machineToGraphNodeMapping;
  };

  const machineIDToGraphNodeMapping = getMachineIDToGraphNodeMapping();
  const initialParadiseNodes = Object.values(
    machineIDToGraphNodeMapping
  ).flatMap((x) => x);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialParadiseNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialParadiseEdges(machineIDToGraphNodeMapping)
  );

  return (
    <ReactFlow
      nodeTypes={nodeTypes}
      nodes={nodes}
      edges={edges}
      panOnScroll
      fitView
    >
      <Background />
      <MiniMap />
      <Controls />
    </ReactFlow>
  );
}


export default function Index() {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", lineHeight: "1.8" }}>
      <div className="h-[50vh]">
        {window && <Editor />}
      </div> 
      <div className="h-[50vh]">
        {window && <Visualizer />}
      </div> 
    </div>
  );
}