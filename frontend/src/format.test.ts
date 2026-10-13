import { describe, expect, it } from 'vitest'
import { formatLatency, pdfLink, splitAnswer } from './format'

describe('splitAnswer', () => {
  it('sépare le texte, le gras et les renvois', () => {
    expect(splitAnswer('Il faut **15 minutes** [1] avant [2].')).toEqual([
      { kind: 'text', value: 'Il faut ' },
      { kind: 'bold', value: '15 minutes' },
      { kind: 'text', value: ' ' },
      { kind: 'citation', number: 1 },
      { kind: 'text', value: ' avant ' },
      { kind: 'citation', number: 2 },
      { kind: 'text', value: '.' },
    ])
  })

  it('renvoie le texte tel quel sans balise', () => {
    expect(splitAnswer('Je ne trouve pas.')).toEqual([{ kind: 'text', value: 'Je ne trouve pas.' }])
  })
})

describe('pdfLink', () => {
  it('ajoute le numéro de page et remplace un fragment existant', () => {
    expect(pdfLink('https://ex.org/doc.pdf', 7)).toBe('https://ex.org/doc.pdf#page=7')
    expect(pdfLink('https://ex.org/doc.pdf#page=2', 7)).toBe('https://ex.org/doc.pdf#page=7')
  })
})

describe('formatLatency', () => {
  it('affiche des millisecondes ou des secondes à la française', () => {
    expect(formatLatency(850.4)).toBe('850 ms')
    expect(formatLatency(10482)).toBe('10,5 s')
  })
})
