import { createDbWorker, type WorkerHttpvfs } from "sql.js-httpvfs";
import sqliteWorkerUrl from "sql.js-httpvfs/dist/sqlite.worker.js?url";
import sqlWasmUrl from "sql.js-httpvfs/dist/sql-wasm.wasm?url";

import {
  BuildsResponse,
  LastCheck,
  UnparsedBuild,
  UnparsedItem,
  Options,
} from "./types";

const ARCHIVE_DB_URL = "/archive/builds.sqlite3";
const LAST_CHECK_URL = "/archive/last-check.json";
const OPTIONS_URL = "/archive/options.json";
const PAGE_SIZE = 10;
const REQUEST_CHUNK_SIZE = 1024;

interface ArchiveBuildRow {
  id: number;
  season: number;
  league: string;
  phase: string;
  date: string;
  match_url: string;
  game_i: number;
  win: number;
  game_length: string;
  kda_ratio: number;
  kills: number;
  deaths: number;
  assists: number;
  role: string;
  player1: string;
  god1: string;
  team1: string;
  player2: string;
  god2: string;
  team2: string;
}

interface ArchiveBuildItemRow {
  build_id: number;
  is_relic: number;
  slot_index: number;
  name: string;
  image_mime_type: string | null;
  image_data: string | null;
}

interface QueryParts {
  clauses: string[];
  params: Array<number | string>;
}

export const getLastCheck = async (): Promise<LastCheck> =>
  fetchArchiveJson<LastCheck>(LAST_CHECK_URL);

export const getOptions = async (): Promise<Options> =>
  fetchArchiveJson<Options>(OPTIONS_URL);

export const getBuilds = async (
  searchParams: URLSearchParams,
  page: number
): Promise<BuildsResponse> => {
  const { db } = await getArchiveDb();
  const queryParts = getQueryParts(searchParams);
  const whereSql = getWhereSql(queryParts);

  let count: number | null = null;
  if (page === 1) {
    const countRows = (await db.query(
      `SELECT COUNT(*) AS count FROM build ${whereSql}`,
      queryParts.params
    )) as Array<{ count: number }>;
    count = countRows[0]?.count ?? 0;
  }

  const buildRows = (await db.query(
    `
    SELECT
      id,
      season,
      league,
      phase,
      date,
      match_url,
      game_i,
      win,
      game_length,
      ROUND(kda_ratio, 1) AS kda_ratio,
      kills,
      deaths,
      assists,
      role,
      player1,
      god1,
      team1,
      player2,
      god2,
      team2
    FROM build
    ${whereSql}
    ORDER BY date DESC, match_id DESC, game_i DESC, win DESC, role ASC
    LIMIT ? OFFSET ?
    `,
    [...queryParts.params, PAGE_SIZE, (page - 1) * PAGE_SIZE]
  )) as ArchiveBuildRow[];

  if (buildRows.length === 0) {
    return { count, builds: [] };
  }

  const buildIds = buildRows.map((row) => row.id);
  const buildItemsByBuildId = await getBuildItemsByBuildId(db, buildIds);
  const builds = buildRows.map((row): UnparsedBuild => {
    const buildItems = buildItemsByBuildId.get(row.id);
    return {
      ...row,
      win: Boolean(row.win),
      relics: buildItems?.relics ?? [null, null],
      items: buildItems?.items ?? [null, null, null, null, null, null],
    };
  });
  return { count, builds };
};

const fetchArchiveJson = async <T>(url: string): Promise<T> => {
  const response = await fetch(url);
  if (!response.ok) {
    throw Error(
      `HTTP error! Status: ${response.status} ${response.statusText}`
    );
  }
  return response.json();
};

let archiveDbFuture: Promise<WorkerHttpvfs> | null = null;

const getArchiveDb = async (): Promise<WorkerHttpvfs> => {
  if (archiveDbFuture === null) {
    archiveDbFuture = createDbWorker(
      [
        {
          from: "inline",
          config: {
            serverMode: "full",
            url: ARCHIVE_DB_URL,
            requestChunkSize: REQUEST_CHUNK_SIZE,
          },
        },
      ],
      sqliteWorkerUrl,
      sqlWasmUrl
    );
  }
  return archiveDbFuture;
};

const getBuildItemsByBuildId = async (
  db: WorkerHttpvfs["db"],
  buildIds: number[]
): Promise<
  Map<
    number,
    { relics: Array<UnparsedItem | null>; items: Array<UnparsedItem | null> }
  >
> => {
  const placeholders = buildIds.map(() => "?").join(", ");
  const buildItemRows = (await db.query(
    `
    SELECT
      build_item.build_id,
      build_item.is_relic,
      build_item.slot_index,
      build_item.display_name AS name,
      image.mime_type AS image_mime_type,
      image.data AS image_data
    FROM build_item
    LEFT JOIN image ON image.id = build_item.image_id
    WHERE build_item.build_id IN (${placeholders})
    ORDER BY build_item.build_id ASC, build_item.is_relic DESC, build_item.slot_index ASC
    `,
    buildIds
  )) as ArchiveBuildItemRow[];

  const buildItemsByBuildId = new Map<
    number,
    { relics: Array<UnparsedItem | null>; items: Array<UnparsedItem | null> }
  >();
  for (const row of buildItemRows) {
    const buildItems =
      buildItemsByBuildId.get(row.build_id) ?? createEmptyBuildItems();
    const item = {
      name: row.name,
      image_mime_type: row.image_mime_type,
      image_data: row.image_data,
    };
    if (row.is_relic) {
      buildItems.relics[row.slot_index] = item;
    } else {
      buildItems.items[row.slot_index] = item;
    }
    buildItemsByBuildId.set(row.build_id, buildItems);
  }
  return buildItemsByBuildId;
};

const createEmptyBuildItems = () => ({
  relics: [null, null] as Array<UnparsedItem | null>,
  items: [null, null, null, null, null, null] as Array<UnparsedItem | null>,
});

const getQueryParts = (searchParams: URLSearchParams): QueryParts => {
  const queryParts: QueryParts = { clauses: [], params: [] };

  addInClause(queryParts, "season", getNumberValues(searchParams, "season"));
  addInClause(queryParts, "league", searchParams.getAll("league"));
  addInClause(queryParts, "phase", searchParams.getAll("phase"));
  addRangeClause(queryParts, "date", getTextRange(searchParams, "date"));
  addInClause(queryParts, "game_i", getNumberValues(searchParams, "game_i"));
  addRangeClause(
    queryParts,
    "game_length",
    getTextRange(searchParams, "game_length")
  );
  addInClause(queryParts, "win", getBooleanValues(searchParams, "win"));
  addRangeClause(
    queryParts,
    "kda_ratio",
    getNumberRange(searchParams, "kda_ratio")
  );
  addRangeClause(queryParts, "kills", getNumberRange(searchParams, "kills"));
  addRangeClause(queryParts, "deaths", getNumberRange(searchParams, "deaths"));
  addRangeClause(
    queryParts,
    "assists",
    getNumberRange(searchParams, "assists")
  );
  addInClause(queryParts, "role", searchParams.getAll("role"));
  addInClause(queryParts, "god_class", searchParams.getAll("god_class"));
  addInClause(queryParts, "god1", searchParams.getAll("god1"));
  addInClause(queryParts, "player1", searchParams.getAll("player1"));
  addInClause(queryParts, "team1", searchParams.getAll("team1"));
  addInClause(queryParts, "god2", searchParams.getAll("god2"));
  addInClause(queryParts, "player2", searchParams.getAll("player2"));
  addInClause(queryParts, "team2", searchParams.getAll("team2"));
  addItemClauses(queryParts, "relic", true, searchParams.getAll("relic"));
  addItemClauses(queryParts, "item", false, searchParams.getAll("item"));

  return queryParts;
};

const addInClause = (
  queryParts: QueryParts,
  column: string,
  values: Array<number | string>
) => {
  if (values.length === 0) {
    return;
  }
  const placeholders = values.map(() => "?").join(", ");
  queryParts.clauses.push(`${column} IN (${placeholders})`);
  queryParts.params.push(...values);
};

const addRangeClause = (
  queryParts: QueryParts,
  column: string,
  range: [number | string, number | string] | null
) => {
  if (range === null) {
    return;
  }
  queryParts.clauses.push(`? <= ${column}`);
  queryParts.clauses.push(`${column} <= ?`);
  queryParts.params.push(...range);
};

const addItemClauses = (
  queryParts: QueryParts,
  _label: string,
  isRelic: boolean,
  names: string[]
) => {
  for (const name of names) {
    queryParts.clauses.push(
      `
      id IN (
        SELECT build_id
        FROM build_item
        WHERE is_relic = ? AND search_name = ?
      )
      `
    );
    queryParts.params.push(isRelic ? 1 : 0, name);
  }
};

const getWhereSql = (queryParts: QueryParts) =>
  queryParts.clauses.length === 0
    ? ""
    : `WHERE ${queryParts.clauses.join(" AND ")}`;

const getNumberValues = (searchParams: URLSearchParams, key: string) =>
  searchParams.getAll(key).map((value) => Number(value));

const getBooleanValues = (searchParams: URLSearchParams, key: string) =>
  searchParams.getAll(key).map((value) => (value === "true" ? 1 : 0));

const getNumberRange = (
  searchParams: URLSearchParams,
  key: string
): [number, number] | null => {
  const values = searchParams.getAll(key);
  if (values.length !== 2) {
    return null;
  }
  return [Number(values[0]), Number(values[1])];
};

const getTextRange = (
  searchParams: URLSearchParams,
  key: string
): [string, string] | null => {
  const values = searchParams.getAll(key);
  if (values.length !== 2) {
    return null;
  }
  return [values[0], values[1]];
};
