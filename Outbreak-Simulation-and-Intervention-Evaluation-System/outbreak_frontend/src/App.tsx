import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import axios from 'axios';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || 'http://127.0.0.1:8001';

const COLOR_MAP: Record<number, string> = {
  0: '#94a3b8',
  1: '#f87171',
  2: '#60a5fa',
  3: '#34d399',
  4: '#1f2937',
};

const STRATEGY_OPTIONS = ['celf', 'degree', 'random', 'betweenness', 'pagerank', 'k_core', 'closeness'];

type GraphData = {
  nodes: Array<{ id: number; group: number; x?: number; y?: number }>;
  links: Array<{ source: number; target: number; weight?: number }>;
};

type EvalResult = {
  strategy: string;
  mean_spread?: number;
  std_spread?: number;
  median_spread?: number;
  peak_spreaders_mean?: number;
  curve_mean?: number[];
  curve_lower?: number[];
  curve_upper?: number[];
  timeline_steps?: number[];
  mean_reduction?: number;
  reduction_pct?: number;
  p_value_vs_none?: number;
  nodes?: number[];
};

const defaultConfig = {
  network_type: 'campus',
  num_nodes: 120,
  beta: 0.2,
  gamma: 0.08,
  delta: 0.12,
  seed: 42,
  source_nodes: [0],
  intervention_nodes: [5],
  intervention_type: 'blocked',
  max_steps: 20,
  k: 5,
};

function App() {
  const [network, setNetwork] = useState<GraphData>({ nodes: [], links: [] });
  const [timeline, setTimeline] = useState<number[][]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState(defaultConfig);
  const [selectedStrategy, setSelectedStrategy] = useState('celf');
  const [selectedInterventionNodes, setSelectedInterventionNodes] = useState<number[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  const [comparisonData, setComparisonData] = useState<{ baseline: number[][]; intervention: number[][] }>({
    baseline: [],
    intervention: [],
  });
  const [evaluationResults, setEvaluationResults] = useState<Record<string, EvalResult>>({});
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [graphSize, setGraphSize] = useState({ width: 800, height: 520 });
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const forceGraphRef = useRef<any>(null);

  useEffect(() => {
    if (!graphContainerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      setGraphSize({ width: rect.width, height: Math.max(rect.height, 420) });
    });
    observer.observe(graphContainerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!forceGraphRef.current || network.nodes.length === 0) return;
    forceGraphRef.current.zoomToFit(500, 40);
  }, [network, graphSize]);

  const generateNetwork = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API_BASE}/network/generate`, config);
      setNetwork({ nodes: res.data.nodes, links: res.data.links });
      setSummary(res.data.summary ?? {});
      setSelectedInterventionNodes(res.data.summary?.intervention_nodes ?? []);
    } catch (err) {
      setError('Unable to generate the network from the backend.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [config]);

  const runSimulation = useCallback(async (overrideConfig = config) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API_BASE}/simulate`, overrideConfig);
      const nextTimeline = res.data.timeline ?? [];
      setTimeline(nextTimeline);
      setCurrentStep(0);
      setIsPlaying(true);
      return nextTimeline;
    } catch (err) {
      setError('Simulation request failed. Check the backend server and configuration.');
      console.error(err);
      return [];
    } finally {
      setLoading(false);
    }
  }, [config]);

  useEffect(() => {
    if (!isPlaying || timeline.length === 0) return;
    const timer = window.setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= timeline.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 450);
    return () => window.clearInterval(timer);
  }, [isPlaying, timeline]);

  const selectInterventions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = { ...config, intervention_nodes: config.intervention_nodes ?? [] };
      const selectedRes = await axios.post(`${API_BASE}/select?k=${config.k}&strategy=${selectedStrategy}`, payload);
      const chosen = selectedRes.data.selected ?? [];
      setSelectedInterventionNodes(chosen);
      setConfig((prev) => ({ ...prev, intervention_nodes: chosen }));

      const withIntervention = { ...payload, intervention_nodes: chosen, intervention_type: config.intervention_type };
      const [baselineRun, interventionRun] = await Promise.all([
        axios.post(`${API_BASE}/simulate`, { ...payload, intervention_nodes: [] }),
        axios.post(`${API_BASE}/simulate`, withIntervention),
      ]);

      setComparisonData({
        baseline: baselineRun.data.timeline ?? [],
        intervention: interventionRun.data.timeline ?? [],
      });
      setTimeline(interventionRun.data.timeline ?? []);
      setCurrentStep(0);
      setShowComparison(true);
    } catch (err) {
      setError('Unable to select interventions and compare them.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [config, selectedStrategy]);

  const runEvaluation = useCallback(async () => {
    setEvaluationLoading(true);
    setError(null);
    try {
      const list = Array.from(new Set(['degree', selectedStrategy, 'celf']));
      const res = await axios.post(`${API_BASE}/evaluate`, {
        ...config,
        intervention_nodes: selectedInterventionNodes.length ? selectedInterventionNodes : config.intervention_nodes,
      }, {
        params: {
          k: config.k,
          strategies: list,
        },
      });
      setEvaluationResults(res.data.results ?? {});
    } catch (err) {
      const detail = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : 'Unknown backend error';
      setError(`Evaluation failed: ${detail}`);
      console.error(err);
    } finally {
      setEvaluationLoading(false);
    }
  }, [config, selectedInterventionNodes, selectedStrategy]);

  const currentTimeline = useMemo(() => {
    if (showComparison) {
      return comparisonData.intervention.length ? comparisonData.intervention : timeline;
    }
    return timeline;
  }, [comparisonData, showComparison, timeline]);

  const nodesAtStep = useMemo(() => {
    if (!currentTimeline.length) return {} as Record<number, number>;
    const current = currentTimeline[Math.min(currentStep, currentTimeline.length - 1)] ?? [];
    return Object.fromEntries(current.map((state, idx) => [idx, state]));
  }, [currentStep, currentTimeline]);

  const paintNodeForTimeline = useCallback((timelineSource: number[][], interventionSet: number[]) => (node: any, ctx: CanvasRenderingContext2D) => {
    const currentStepStates = timelineSource[Math.min(currentStep, timelineSource.length - 1)] ?? [];
    const state = currentStepStates[node.id] ?? 0;
    const color = COLOR_MAP[state] ?? COLOR_MAP[0];
    const nodeRadius = 5.2;

    ctx.beginPath();
    ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI, false);
    ctx.fillStyle = color;
    ctx.shadowColor = interventionSet.includes(node.id) ? 'rgba(96, 165, 250, 0.9)' : 'transparent';
    ctx.shadowBlur = interventionSet.includes(node.id) ? 14 : 0;
    ctx.fill();
    ctx.shadowBlur = 0;

    const isSource = config.source_nodes.includes(node.id);
    const isIntervention = interventionSet.includes(node.id);

    if (isSource || isIntervention) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius + (isSource ? 5 : 4), 0, 2 * Math.PI, false);
      ctx.strokeStyle = isSource ? '#facc15' : '#7dd3fc';
      ctx.lineWidth = isSource ? 2.4 : 1.5;
      ctx.setLineDash(isSource ? [] : [4, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.beginPath();
    ctx.arc(node.x, node.y, nodeRadius + 0.8, 0, 2 * Math.PI, false);
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1.1;
    ctx.stroke();
  }, [config.source_nodes, currentStep]);

  const effectiveStats = useMemo(() => {
    const totalNodes = Math.max(network.nodes.length || summary.num_nodes || 1, 1);
    if (!currentTimeline.length) {
      return {
        infectedCount: 0,
        currentlySpreading: 0,
        peakSpreaders: 0,
        everInfected: 0,
        everInfectedPct: 0,
      };
    }

    const currentFrame = currentTimeline[Math.min(currentStep, currentTimeline.length - 1)] ?? [];
    const currentlySpreading = currentFrame.filter((state) => state === 1).length;
    const peakSpreaders = Math.max(...currentTimeline.map((frame) => frame.filter((state) => state === 1).length), 0);
    const everInfectedSet = new Set<number>();
    currentTimeline.forEach((frame) => {
      frame.forEach((state, idx) => {
        if (state === 1 || state === 2 || state === 3) everInfectedSet.add(idx);
      });
    });
    const everInfected = everInfectedSet.size;

    return {
      infectedCount: currentFrame.filter((state) => state === 1 || state === 2).length,
      currentlySpreading,
      peakSpreaders,
      everInfected,
      everInfectedPct: totalNodes ? everInfected / totalNodes : 0,
    };
  }, [currentStep, currentTimeline, network.nodes.length, summary.num_nodes]);

  const chartData = useMemo(() => {
    const baselineCurve = comparisonData.baseline?.[0] ? comparisonData.baseline : timeline;
    const interventionCurve = comparisonData.intervention?.[0] ? comparisonData.intervention : timeline;

    const maxLength = Math.max(baselineCurve.length, interventionCurve.length, 1);
    return Array.from({ length: maxLength }, (_, idx) => ({
      step: idx,
      baseline: baselineCurve[idx]?.filter((state) => state === 1 || state === 2).length ?? 0,
      intervention: interventionCurve[idx]?.filter((state) => state === 1 || state === 2).length ?? 0,
    }));
  }, [comparisonData, timeline]);

  const comparisonBarData = useMemo(() => {
    const records = Object.entries(evaluationResults).map(([key, result]) => ({
      name: key,
      mean_spread: result.mean_spread ?? 0,
      std_spread: result.std_spread ?? 0,
      strategy: result.strategy ?? key,
    }));
    return records.sort((a, b) => (a.mean_spread ?? 0) - (b.mean_spread ?? 0));
  }, [evaluationResults]);

  const runSelectedSimulation = useCallback(async () => {
    if (selectedInterventionNodes.length) {
      await runSimulation({ ...config, intervention_nodes: selectedInterventionNodes });
      return;
    }
    await runSimulation();
  }, [config, runSimulation, selectedInterventionNodes]);

  return (
    <div className="app-shell">
      <aside className="panel side-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Simulation Setup</p>
            <h1>Outbreak of Lies</h1>
          </div>
        </div>

        <div className="field-grid">
          <label>
            <span>Network</span>
            <select value={config.network_type} onChange={(e) => setConfig({ ...config, network_type: e.target.value })}>
              <option value="campus">Campus</option>
              <option value="ba">Barabasi-Albert</option>
              <option value="ws">Watts-Strogatz</option>
              <option value="trap">Trap</option>
            </select>
          </label>

          <label>
            <span>Nodes</span>
            <input type="number" value={config.num_nodes} onChange={(e) => setConfig({ ...config, num_nodes: Number(e.target.value) })} />
          </label>

          <label>
            <span>Budget k</span>
            <input type="number" min={1} value={config.k} onChange={(e) => setConfig({ ...config, k: Number(e.target.value) || 1 })} />
          </label>

          <label>
            <span>Beta</span>
            <input type="number" step="0.01" value={config.beta} onChange={(e) => setConfig({ ...config, beta: Number(e.target.value) })} />
          </label>

          <label>
            <span>Gamma</span>
            <input type="number" step="0.01" value={config.gamma} onChange={(e) => setConfig({ ...config, gamma: Number(e.target.value) })} />
          </label>

          <label>
            <span>Delta</span>
            <input type="number" step="0.01" value={config.delta} onChange={(e) => setConfig({ ...config, delta: Number(e.target.value) })} />
          </label>

          <label>
            <span>Seed</span>
            <input type="number" value={config.seed} onChange={(e) => setConfig({ ...config, seed: Number(e.target.value) })} />
          </label>

          <label>
            <span>Strategy</span>
            <select value={selectedStrategy} onChange={(e) => setSelectedStrategy(e.target.value)}>
              {STRATEGY_OPTIONS.map((strategy) => (
                <option key={strategy} value={strategy}>
                  {strategy}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Intervention</span>
            <select value={config.intervention_type} onChange={(e) => setConfig({ ...config, intervention_type: e.target.value })}>
              <option value="blocked">Blocked</option>
              <option value="immune">Immune</option>
            </select>
          </label>
        </div>

        <div className="button-row">
          <button className="primary" onClick={generateNetwork} disabled={loading}>Generate graph</button>
          <button className="secondary" onClick={runSelectedSimulation} disabled={loading || network.nodes.length === 0}>Run sim</button>
          <button className="ghost" onClick={selectInterventions} disabled={loading || network.nodes.length === 0}>Select interventions</button>
          <button className="ghost" onClick={() => setShowComparison((value) => !value)} disabled={!comparisonData.baseline.length && !comparisonData.intervention.length}>Compare</button>
          <button className="ghost" onClick={runEvaluation} disabled={evaluationLoading || network.nodes.length === 0}>
            {evaluationLoading ? 'Evaluating…' : 'Evaluate'}
          </button>
        </div>

        {error && <div className="error-box">{error}</div>}

        <div className="stats-grid">
          <div className="stat-box">
            <span>Nodes</span>
            <strong>{summary.num_nodes ?? network.nodes.length}</strong>
          </div>
          <div className="stat-box">
            <span>Edges</span>
            <strong>{summary.num_edges ?? network.links.length}</strong>
          </div>
          <div className="stat-box">
            <span>Density</span>
            <strong>{summary.density ? summary.density.toFixed(3) : '—'}</strong>
          </div>
          <div className="stat-box">
            <span>Ever infected</span>
            <strong>{effectiveStats.everInfected}</strong>
            <small>{(effectiveStats.everInfectedPct * 100).toFixed(1)}% of network</small>
          </div>
          <div className="stat-box">
            <span>Currently spreading</span>
            <strong>{effectiveStats.currentlySpreading}</strong>
          </div>
          <div className="stat-box">
            <span>Peak spreaders</span>
            <strong>{effectiveStats.peakSpreaders}</strong>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <div className="top-strip">
          <div className="legend">
            <span><i className="dot susceptible" /> Susceptible</span>
            <span><i className="dot spreader" /> Spreader</span>
            <span><i className="dot stifler" /> Stifler</span>
            <span><i className="dot immune" /> Immune</span>
            <span><i className="dot blocked" /> Blocked</span>
          </div>
          <div className="step-indicator">Step {currentStep} / {Math.max(currentTimeline.length - 1, 0)}</div>
        </div>

        <div ref={graphContainerRef} className="network-panel">
          {network.nodes.length > 0 ? (
            showComparison && comparisonData.baseline.length && comparisonData.intervention.length ? (
              <div className="comparison-grid">
                <div className="comparison-panel">
                  <div className="comparison-header">No intervention</div>
                  <ForceGraph2D
                    ref={forceGraphRef}
                    width={graphSize.width / 2 - 12}
                    height={graphSize.height - 48}
                    graphData={network}
                    nodeCanvasObject={paintNodeForTimeline(comparisonData.baseline.length ? comparisonData.baseline : timeline, [])}
                    nodeCanvasObjectMode={() => 'replace'}
                    linkDirectionalParticles={1}
                    linkDirectionalParticleWidth={1.5}
                    linkColor={() => '#475569'}
                    backgroundColor="#0f172a"
                    enableNodeDrag={false}
                    onNodeDragEnd={() => undefined}
                  />
                </div>
                <div className="comparison-panel">
                  <div className="comparison-header">With intervention</div>
                  <ForceGraph2D
                    width={graphSize.width / 2 - 12}
                    height={graphSize.height - 48}
                    graphData={network}
                    nodeCanvasObject={paintNodeForTimeline(comparisonData.intervention.length ? comparisonData.intervention : currentTimeline, selectedInterventionNodes)}
                    nodeCanvasObjectMode={() => 'replace'}
                    linkDirectionalParticles={1}
                    linkDirectionalParticleWidth={1.5}
                    linkColor={() => '#475569'}
                    backgroundColor="#0f172a"
                    enableNodeDrag={false}
                    onNodeDragEnd={() => undefined}
                  />
                </div>
              </div>
            ) : (
              <ForceGraph2D
                ref={forceGraphRef}
                width={graphSize.width}
                height={graphSize.height}
                graphData={network}
                nodeCanvasObject={paintNodeForTimeline(currentTimeline, selectedInterventionNodes)}
                nodeCanvasObjectMode={() => 'replace'}
                linkDirectionalParticles={1}
                linkDirectionalParticleWidth={1.5}
                linkColor={() => '#475569'}
                backgroundColor="#0f172a"
                enableNodeDrag={false}
                onNodeDragEnd={() => undefined}
              />
            )
          ) : (
            <div className="empty-state">Generate a network to start the simulation.</div>
          )}
        </div>

        <div className="timeline-bar">
          <input
            type="range"
            min={0}
            max={Math.max(currentTimeline.length - 1, 0)}
            value={currentStep}
            onChange={(e) => setCurrentStep(Number(e.target.value))}
          />
        </div>

        {Object.keys(evaluationResults).length > 0 && (
          <div className="evaluation-panel">
            <div className="evaluation-header">
              <h2>Evaluation dashboard</h2>
            </div>

            <div className="chart-grid">
              <div className="chart-card wide">
                <h3>Infection curve</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="step" stroke="#cbd5e1" />
                    <YAxis stroke="#cbd5e1" />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="baseline" fill="#f59e0b" fillOpacity={0.08} stroke="#f59e0b" />
                    <Area type="monotone" dataKey="intervention" fill="#38bdf8" fillOpacity={0.08} stroke="#38bdf8" />
                    <Line type="monotone" dataKey="baseline" stroke="#f59e0b" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="intervention" stroke="#38bdf8" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-card">
                <h3>Strategy impact</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={comparisonBarData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="name" stroke="#cbd5e1" />
                    <YAxis stroke="#cbd5e1" />
                    <Tooltip />
                    <Bar dataKey="mean_spread" fill="#38bdf8">
                      <ErrorBar dataKey="std_spread" width={4} strokeWidth={1.4} stroke="#f8fafc" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="leaderboard-card">
              <h3>Leaderboard</h3>
              <div className="leaderboard-list">
                {comparisonBarData.map((entry, index) => (
                  <div key={entry.name} className="leaderboard-item">
                    <span className="rank">#{index + 1}</span>
                    <span className="strategy-name">{entry.name}</span>
                    <span className="strategy-score">{entry.mean_spread.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
