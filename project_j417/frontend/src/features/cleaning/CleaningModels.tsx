import { useCleaningModels, useCleaningSummary, useTrainCleaning } from "./hooks";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

function Badge({ on }: { on: boolean }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${on ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
      {on ? "trained model in use" : "hand-written rule in use"}
    </span>
  );
}

export default function CleaningModels() {
  const { data } = useCleaningModels();
  const summary = useCleaningSummary().data?.summary;
  const train = useTrainCleaning();
  const report = data?.report;
  const inUse = data?.in_use;

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <h2 className="text-lg font-semibold">3. Train the cleaning models</h2>
          <p className="mt-1 text-sm text-slate-600">
            Three small models decide which parts of each JSON are worth keeping, with no one reviewing the videos. They learn
            from examples made automatically from your own transcripts:
          </p>
          <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-slate-600">
            <li><b>Sentence model:</b> finds sentences with no content (“subscribe”, thank-you endings, sponsor reads).</li>
            <li><b>Word model:</b> finds error words (“um”, “you know”, words said twice).</li>
            <li><b>Duplicate model:</b> finds the same sentence said twice.</li>
          </ul>
          <p className="mt-2 text-sm text-slate-600">
            Each one is tested on data it never saw and compared with a simple hand-written rule. A model is used only if it is
            at least as good as the rule.
          </p>
        </div>
        <button
          onClick={() => train.mutate()}
          disabled={train.isPending}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {train.isPending ? "Training…" : report ? "Train again" : "Train the models"}
        </button>
      </div>

      {train.isPending && <p className="text-sm text-slate-500">Making practice data, training and testing take about 30 seconds.</p>}
      {train.error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {train.error.message}
        </p>
      )}
      {!report && !train.isPending && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Not trained yet, so the JSON files are cleaned with the hand-written rules. Press <b>Train the models</b>.
        </p>
      )}

      {report && inUse && (
        <div className="space-y-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                <th className="py-1 font-medium">Job</th>
                <th className="py-1 font-medium">Trained model (tested on unseen data)</th>
                <th className="py-1 font-medium">Hand-written rule</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-100 align-top">
                <td className="py-2 pr-3">
                  <p className="font-medium">Redundant sentences</p>
                  <Badge on={inUse.sentences} />
                </td>
                <td className="py-2 pr-3">
                  Finds <b>{pct(report.sentences.model.caught)}</b> of them
                  <span className="block text-xs text-slate-500">{pct(report.sentences.model.wrongly_flagged)} of real content removed by mistake</span>
                </td>
                <td className="py-2">
                  Finds {pct(report.sentences.rules.caught)}
                  <span className="block text-xs text-slate-500">{pct(report.sentences.rules.wrongly_flagged)} removed by mistake</span>
                </td>
              </tr>
              <tr className="border-b border-slate-100 align-top">
                <td className="py-2 pr-3">
                  <p className="font-medium">Error words</p>
                  <Badge on={inUse.words} />
                </td>
                <td className="py-2 pr-3">
                  Fully repairs <b>{pct(report.words.model.restored_exactly)}</b> of damaged sentences
                  <span className="block text-xs text-slate-500">changes {pct(report.words.model.false_edit_rate)} of clean sentences by mistake</span>
                </td>
                <td className="py-2">
                  Fully repairs {pct(report.words.rules.restored_exactly)}
                  <span className="block text-xs text-slate-500">changes {pct(report.words.rules.false_edit_rate)} by mistake</span>
                </td>
              </tr>
              <tr className="border-b border-slate-100 align-top">
                <td className="py-2 pr-3">
                  <p className="font-medium">Duplicates</p>
                  <Badge on={inUse.duplicates} />
                </td>
                <td className="py-2 pr-3">
                  Finds <b>{pct(report.duplicates.model.caught)}</b> of duplicate pairs
                  <span className="block text-xs text-slate-500">{pct(report.duplicates.model.wrongly_flagged)} of different sentences merged by mistake</span>
                </td>
                <td className="py-2">
                  Finds {pct(report.duplicates.rules.caught)}
                  <span className="block text-xs text-slate-500">{pct(report.duplicates.rules.wrongly_flagged)} merged by mistake (best fixed threshold)</span>
                </td>
              </tr>
            </tbody>
          </table>

          {summary && (
            <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
              <p className="font-medium">What the cleaning did to your {summary.videos} videos</p>
              <p className="mt-1">
                {summary.segments_raw.toLocaleString()} → {summary.segments_kept.toLocaleString()} segments · {summary.words_removed_pct}% of words removed ·{" "}
                {summary.redundant_sentences_removed} redundant sentences · {summary.error_words_removed} error words ·{" "}
                {(summary.removed.duplicate_in_video ?? 0) + (summary.removed.duplicate_across_videos ?? 0)} duplicates
              </p>
            </div>
          )}

          <details className="text-sm text-slate-600">
            <summary className="cursor-pointer text-xs font-medium text-slate-500">How was each model trained and tested?</summary>
            <div className="mt-2 space-y-3 text-xs">
              <p>
                <b>Sentence model:</b> learned from {report.sentences.examples.redundant} labeled redundant sentences ({report.sentences.examples.kinds.length} kinds)
                and {report.sentences.examples.real_sentences + report.sentences.examples.tricky_content} normal ones ({report.sentences.examples.real_sentences} from your videos). On a whole
                kind it was never shown, it still found {pct(report.sentences.never_seen_kind.caught)}, so it needs examples of each kind.
              </p>
              <p>
                <b>Word model:</b> {report.words.examples.clean_sentences} clean real sentences were damaged on purpose ({report.words.examples.filler_kinds} kinds of filler, plus repeated
                words), so the right answer is known. Tested on {report.words.test_sentences} damaged sentences it never saw; it removes a word only when it is at
                least {Math.round(report.words.model.threshold * 100)}% sure. It finds {pct(report.words.model.error_words_caught)} of the error words with {pct(report.words.model.error_words_precision)} precision.
              </p>
              <p>
                <b>Duplicate model:</b> learned from {report.duplicates.examples.pairs} sentence pairs (a sentence and a noisy copy, versus different or look-alike sentences) how to weigh five
                similarity signals instead of using one overlap number.
              </p>
              {report.sentences.on_your_videos.examples.length > 0 && (
                <div>
                  <p className="font-medium">Sentences the sentence model flagged in your videos. Do you agree they carry no content?</p>
                  <ul className="list-disc pl-5">
                    {report.sentences.on_your_videos.examples.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
              <p>
                The test data is made from your own transcripts with known mistakes added, so the numbers show what each model learned, not performance on every
                possible video. Trained {report.trained_at}.
              </p>
            </div>
          </details>
        </div>
      )}
    </section>
  );
}
