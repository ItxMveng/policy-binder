// Types et appels de l'API FastAPI (miroir des modèles Pydantic de policy_binder).

export interface Chunk {
  id: string
  source_id: string
  title: string
  page: number
  text: string
}

export interface ScoredChunk {
  chunk: Chunk
  score: number
}

export interface Citation {
  number: number
  chunk_id: string
  source_id: string
  title: string
  page: number
}

export interface Answer {
  question: string
  text: string
  abstained: boolean
  citations: Citation[]
  retrieved: ScoredChunk[]
  latency_ms: number
}

export interface SourceInfo {
  id: string
  title: string
  institution: string
  url: string
}

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // corps non JSON : message générique ci-dessous
  }
  return `Erreur ${response.status}`
}

export async function fetchSources(): Promise<SourceInfo[]> {
  const response = await fetch(`${API_URL}/sources`)
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as SourceInfo[]
}

export async function ask(question: string): Promise<Answer> {
  const response = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as Answer
}
