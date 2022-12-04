// Mostly types used by multiple components,
// but also some types which were moved here to
// declutter their corresponding component.

export const enum SliderType {
  Number,
  Date,
  Time,
}

export interface Options {
  season: string[];
  league: string[];
  phase: string[];
  date: [string, string];
  game_i: number[];
  win: boolean[];
  game_length: [string, string];
  kda_ratio: [number, number];
  kills: [number, number];
  deaths: [number, number];
  assists: [number, number];
  role: string[];
  team1: string[];
  player1: string[];
  god1: string[];
  team2: string[];
  player2: string[];
  god2: string[];
  relic: string[];
  item: string[];
}

export type Nullable<T> = { [K in keyof T]: T[K] | null };

export interface UnparsedBuild {
  id: number;
  season: string;
  league: string;
  phase: string;
  date: string;
  match_url: string;
  game_i: number;
  win: boolean;
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
  relic1: UnparsedItem;
  relic2: UnparsedItem;
  item1: UnparsedItem;
  item2: UnparsedItem;
  item3: UnparsedItem;
  item4: UnparsedItem;
  item5: UnparsedItem;
  item6: UnparsedItem;
}

export type Build = {
  [K in keyof UnparsedBuild]: UnparsedBuild[K] extends UnparsedItem
    ? Item
    : UnparsedBuild[K];
};

export interface UnparsedItem {
  name: string;
  image_name: string;
  image_data: string;
}

export interface Item {
  name: string;
  src: string;
}

export type BuildsResponse =
  | { count: number; builds: UnparsedBuild[] }
  | UnparsedBuild[];
