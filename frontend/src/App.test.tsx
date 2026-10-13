import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { Answer, SourceInfo } from './api'

const SOURCES: SourceInfo[] = [
  {
    id: 'ubo-charte-examens',
    title: "Charte des examens de l'Université de Brest",
    institution: 'Université de Brest (UBO)',
    url: 'https://www.univ-brest.fr/charte_des_examens_ubo.pdf',
  },
]

function answer(overrides: Partial<Answer>): Answer {
  return {
    question: 'q',
    text: 'Il faut arriver **15 minutes** avant le début [1].',
    abstained: false,
    citations: [
      {
        number: 1,
        chunk_id: 'ubo-charte-examens-p3-c0',
        source_id: 'ubo-charte-examens',
        title: "Charte des examens de l'Université de Brest",
        page: 3,
      },
    ],
    retrieved: [
      {
        chunk: {
          id: 'ubo-charte-examens-p3-c0',
          source_id: 'ubo-charte-examens',
          title: "Charte des examens de l'Université de Brest",
          page: 3,
          text: "Les étudiants doivent se présenter à l'entrée de la salle au minimum 15 minutes avant.",
        },
        score: 4.2,
      },
    ],
    latency_ms: 10482,
    ...overrides,
  }
}

function mockApi(reply: Answer) {
  const fetchMock = vi.fn(async (url: string) => {
    const body = url.endsWith('/sources') ? SOURCES : reply
    return new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('App', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('affiche la réponse, la citation et le lien vers la page du PDF officiel', async () => {
    const fetchMock = mockApi(answer({}))
    render(<App />)
    await userEvent.type(screen.getByLabelText('Votre question'), "Quand arriver à l'examen ?")
    await userEvent.click(screen.getByRole('button', { name: 'Demander' }))

    expect(await screen.findByText('15 minutes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Voir la source 1' })).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /page 3/ })
    expect(link).toHaveAttribute('href', 'https://www.univ-brest.fr/charte_des_examens_ubo.pdf#page=3')
    expect(screen.getByText('Réponse en 10,5 s')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/ask'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it("présente l'abstention sans source", async () => {
    mockApi(
      answer({
        text: 'Je ne trouve pas cette information dans les documents.',
        abstained: true,
        citations: [],
      }),
    )
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: /prix du repas/ }))
    expect(await screen.findByText(/adressez-vous au service concerné/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /page/ })).not.toBeInTheDocument()
  })
})
