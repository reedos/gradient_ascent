// /worksheet.md: the worksheet's decision tree as text. The page at /worksheet/ is an interactive
// island, which is no use to a program or to a reader without JavaScript.
import type { APIRoute } from 'astro';
import { worksheetBlocks, toMarkdown, WORKSHEET_TITLE } from '../lib/agents';
import { agentLevels, agentWorksheet, absFor } from '../lib/agents-data';

export const GET: APIRoute = ({ site }) =>
  new Response(toMarkdown(WORKSHEET_TITLE, worksheetBlocks(agentWorksheet(), agentLevels(), absFor(site))), {
    headers: { 'content-type': 'text/markdown; charset=utf-8' },
  });
