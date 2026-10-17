import { useEffect, useState, type FormEvent } from "react";
import { ask, fetchSources, type Answer, type SourceInfo } from "./api";
import { formatLatency, pdfLink, splitAnswer } from "./format";
import "./App.css";

const EXAMPLES = [
  "Combien de temps avant un examen faut-il arriver à l'UBO ?",
  "Puis-je utiliser une IA générative pour un devoir noté ?",
  "Combien de temps peut-on emprunter un livre à la bibliothèque de l'ENIB ?",
  "Quel est le prix du repas au restaurant universitaire ?",
];

function AnswerText({
  answer,
  onCite,
}: {
  answer: Answer;
  onCite: (n: number) => void;
}) {
  return (
    <p className="answer-text">
      {splitAnswer(answer.text).map((segment, index) => {
        if (segment.kind === "bold")
          return <strong key={index}>{segment.value}</strong>;
        if (segment.kind === "text")
          return <span key={index}>{segment.value}</span>;
        const known = answer.citations.some((c) => c.number === segment.number);
        return known ? (
          <button
            key={index}
            type="button"
            className="cite"
            onClick={() => onCite(segment.number)}
            aria-label={`Voir la source ${segment.number}`}
          >
            {segment.number}
          </button>
        ) : null;
      })}
    </p>
  );
}

function Sources({
  answer,
  sources,
}: {
  answer: Answer;
  sources: SourceInfo[];
}) {
  const urls = new Map(sources.map((s) => [s.id, s.url]));
  return (
    <ol className="sources">
      {answer.citations.map((citation) => {
        const passage = answer.retrieved.find(
          (hit) => hit.chunk.id === citation.chunk_id,
        );
        const url = urls.get(citation.source_id);
        return (
          <li key={citation.number} id={`source-${citation.number}`}>
            <div className="source-head">
              <span className="source-number">{citation.number}</span>
              <span className="source-title">{citation.title}</span>
              <span className="source-page">page {citation.page}</span>
            </div>
            {passage && (
              <details>
                <summary>Lire le passage utilisé</summary>
                <blockquote>{passage.chunk.text}</blockquote>
              </details>
            )}
            {url && (
              <a
                href={pdfLink(url, citation.page)}
                target="_blank"
                rel="noreferrer"
              >
                Ouvrir le document officiel à la page {citation.page} ↗
              </a>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSources()
      .then(setSources)
      .catch(() => setSources([]));
  }, []);

  async function submit(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < 3 || loading) return;
    setQuestion(trimmed);
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await ask(trimmed));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(question);
  }

  function scrollToSource(n: number) {
    document
      .getElementById(`source-${n}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="page">
      <header>
        <h1>Le Classeur</h1>
        <p className="tagline">
          Posez votre question sur le règlement : Le Classeur répond en citant
          la page, ou dit qu'il ne sait pas.
        </p>
      </header>

      <form onSubmit={onSubmit} className="ask">
        <label htmlFor="question" className="visually-hidden">
          Votre question
        </label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit(question);
            }
          }}
          placeholder="Ex. : dans quel délai puis-je contester une note ?"
          maxLength={500}
          rows={3}
        />
        <button type="submit" disabled={loading || question.trim().length < 3}>
          {loading ? "Recherche…" : "Demander"}
        </button>
      </form>

      {!answer && !loading && !error && (
        <div className="examples">
          <span>Exemples :</span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => void submit(example)}
            >
              {example}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <p className="status" role="status">
          Recherche dans les règlements… (une dizaine de secondes)
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          Le Classeur n'a pas pu répondre : {error}
        </p>
      )}

      {answer && (
        <section
          className={answer.abstained ? "answer abstained" : "answer"}
          aria-live="polite"
        >
          <AnswerText answer={answer} onCite={scrollToSource} />
          {answer.abstained ? (
            <p className="hint">
              Le Classeur ne consulte que les documents listés ci-dessous. Pour
              cette question, adressez-vous au service concerné.
            </p>
          ) : (
            <>
              {answer.partial && (
                <p className="hint">
                  Une partie de la question n'est pas couverte par les documents
                  consultés : pour celle-ci, adressez-vous au service concerné.
                </p>
              )}
              <Sources answer={answer} sources={sources} />
            </>
          )}
          <p className="meta">Réponse en {formatLatency(answer.latency_ms)}</p>
        </section>
      )}

      <footer>
        <details>
          <summary>Documents consultés ({sources.length})</summary>
          <ul>
            {sources.map((source) => (
              <li key={source.id}>
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.title}
                </a>{" "}
                — {source.institution}
              </li>
            ))}
          </ul>
        </details>
        <p>
          Réponses générées à partir de documents publics de l'ENIB, de
          l'Université de Brest et d'IMT Atlantique. Vérifiez toujours la source
          citée.
        </p>
      </footer>
    </div>
  );
}
