// Loads the committed result files for the pages listed in content/measurements.json. Kept apart
// from results.ts because `import.meta.glob` exists only under Vite, and results.ts is also run
// by plain `node --test`.
import { buildMeasurement, measurementEntries, resultFileName, type Measurement, type ResultFile } from './results';

const files = import.meta.glob<ResultFile>('../../../evals/results/*/*.json', { eager: true, import: 'default' });

function resultFor(example: string, modelId: string): ResultFile {
  const suffix = `/evals/results/${example}/${resultFileName(modelId)}`;
  const key = Object.keys(files).find((k) => k.endsWith(suffix));
  if (!key) throw new Error(`results-data: no committed result file at evals/results/${example}/${resultFileName(modelId)}`);
  return files[key];
}

/** Every measurement for one technique page, in the order content/measurements.json lists them. */
export function measurementsFor(page: string): Measurement[] {
  return measurementEntries.filter((e) => e.page === page).map((e) => buildMeasurement(e, resultFor(e.example, e.model)));
}

/** The first measurement for a page. Throws if the page has none, so a page cannot ask for a result that is not there. */
export function measurementFor(page: string): Measurement {
  const [first] = measurementsFor(page);
  if (!first) throw new Error(`results-data: ${page} has no entry in content/measurements.json`);
  return first;
}
