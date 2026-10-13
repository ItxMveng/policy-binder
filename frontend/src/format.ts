// Fonctions pures de mise en forme des réponses (testées dans format.test.ts).

export type Segment =
  | { kind: 'text'; value: string }
  | { kind: 'bold'; value: string }
  | { kind: 'citation'; number: number }

const TOKEN = /\[(\d+)\]|\*\*(.+?)\*\*/g

/** Découpe la réponse du modèle en texte, passages en gras (**…**) et renvois [n]. */
export function splitAnswer(text: string): Segment[] {
  const segments: Segment[] = []
  let last = 0
  for (const match of text.matchAll(TOKEN)) {
    const index = match.index ?? 0
    if (index > last) segments.push({ kind: 'text', value: text.slice(last, index) })
    if (match[1] !== undefined) segments.push({ kind: 'citation', number: Number(match[1]) })
    else segments.push({ kind: 'bold', value: match[2] })
    last = index + match[0].length
  }
  if (last < text.length) segments.push({ kind: 'text', value: text.slice(last) })
  return segments
}

/** Lien vers le PDF officiel ouvert à la bonne page (fragment #page=N des lecteurs PDF). */
export function pdfLink(url: string, page: number): string {
  return `${url.split('#')[0]}#page=${page}`
}

/** Latence lisible : « 850 ms » ou « 10,5 s ». */
export function formatLatency(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(1).replace('.', ',')} s`
}
