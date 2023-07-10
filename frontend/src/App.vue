<template>
  <div class="section">
    <div class="container">
      <div class="header-thing">
        <div class="update-info">
          <a href="https://www.smiteproleague.com/schedule/">
            https://www.smiteproleague.com/schedule/
          </a>
          <br />
          <span v-bind:title="lastCheck.tooltip">
            Last check: {{ lastCheck.value }}
          </span>
        </div>
        <div class="contact-info">
          <a v-bind:href="`mailto:${antiSpam}`">
            {{ antiSpam }}
          </a>
          <br />
          <a href="https://github.com/NAZADOTH/smite-builds-pro">
            https://github.com/NAZADOTH/smite-builds-pro
          </a>
        </div>
      </div>
      <div class="tabs is-centered is-medium is-boxed">
        <ul>
          <li
            v-bind:class="{ 'is-active': isInBasicView }"
            v-on:click="isInBasicView = true"
          >
            <a>Basic search</a>
          </li>
          <li
            v-bind:class="{ 'is-active': !isInBasicView }"
            v-on:click="isInBasicView = false"
          >
            <a>Advanced search</a>
          </li>
        </ul>
      </div>
      <div v-show="isInBasicView" id="basic-row" class="select-row">
        <MySelect
          id="basic-god"
          v-model:items="basicControls.god.state"
          label="God"
          v-bind:options="options.god1"
        ></MySelect>
        <MySelect
          id="basic-role"
          v-model:items="basicControls.role.state"
          v-bind:options="options.role"
          label="Role"
        ></MySelect>
        <button
          class="button"
          style="margin-left: 2rem"
          v-on:click="refresh(true)"
        >
          Find builds
        </button>
      </div>
      <div v-show="!isInBasicView" id="advanced-row" class="select-row">
        <button
          class="button"
          style="margin-right: 2rem"
          v-on:click="clearControls"
        >
          Clear all
        </button>
        <MySelect
          id="season"
          v-model:items="advancedControls.season.state"
          v-bind:options="options.season"
          label="Seasons"
          multiple
        ></MySelect>
        <MySelect
          id="league"
          v-model:items="advancedControls.league.state"
          v-bind:options="options.league"
          label="Leagues"
          multiple
        ></MySelect>
        <MySelect
          id="phase"
          v-model:items="advancedControls.phase.state"
          v-bind:options="options.phase"
          label="Phases"
          multiple
        ></MySelect>
        <MySlider
          id="date"
          v-model:current="advancedControls.date.state"
          label="Date"
          v-bind:other="{ type: SliderType.Date, unparsedLimit: options.date }"
        ></MySlider>
        <MySelect
          id="game-i"
          v-model:items="advancedControls.gameI.state"
          v-bind:options="options.game_i"
          label="Game #"
          multiple
        ></MySelect>
        <MySlider
          id="game-length"
          v-model:current="advancedControls.gameLength.state"
          label="Game length"
          v-bind:other="{
            type: SliderType.Time,
            unparsedLimit: options.game_length,
          }"
        ></MySlider>
        <MySelect
          id="win"
          v-model:items="advancedControls.win.state"
          v-bind:options="options.win"
          label="Win"
          multiple
        ></MySelect>
        <MySlider
          id="kda-ratio"
          v-model:current="advancedControls.kdaRatio.state"
          label="KDA ratio"
          v-bind:other="{
            type: SliderType.Number,
            unparsedLimit: options.kda_ratio,
            scale: 1,
          }"
        ></MySlider>
        <MySlider
          id="kills"
          v-model:current="advancedControls.kills.state"
          label="Kills"
          v-bind:other="{
            type: SliderType.Number,
            unparsedLimit: options.kills,
            scale: 0,
          }"
        ></MySlider>
        <MySlider
          id="deaths"
          v-model:current="advancedControls.deaths.state"
          label="Deaths"
          v-bind:other="{
            type: SliderType.Number,
            unparsedLimit: options.deaths,
            scale: 0,
          }"
        ></MySlider>
        <MySlider
          id="assists"
          v-model:current="advancedControls.assists.state"
          label="Assists"
          v-bind:other="{
            type: SliderType.Number,
            unparsedLimit: options.assists,
            scale: 0,
          }"
        ></MySlider>
        <MySelect
          id="role"
          v-model:items="advancedControls.role.state"
          v-bind:options="options.role"
          label="Roles"
          multiple
        ></MySelect>
        <MySelect
          id="team1"
          v-model:items="advancedControls.team1.state"
          v-bind:options="options.team1"
          label="Teams"
          multiple
        ></MySelect>
        <MySelect
          id="player1"
          v-model:items="advancedControls.player1.state"
          v-bind:options="options.player1"
          label="Players"
          multiple
        ></MySelect>
        <MySelect
          id="god1"
          v-model:items="advancedControls.god1.state"
          v-bind:options="options.god1"
          label="Gods"
          multiple
        ></MySelect>
        <MySelect
          id="team2"
          v-model:items="advancedControls.team2.state"
          v-bind:options="options.team2"
          label="Opponent teams"
          multiple
        ></MySelect>
        <MySelect
          id="player2"
          v-model:items="advancedControls.player2.state"
          v-bind:options="options.player2"
          label="Opponent players"
          multiple
        ></MySelect>
        <MySelect
          id="god2"
          v-model:items="advancedControls.god2.state"
          v-bind:options="options.god2"
          label="Opponent gods"
          multiple
        ></MySelect>
        <MySelect
          id="relic"
          v-model:items="advancedControls.relic.state"
          v-bind:options="options.relic"
          label="Relics"
          multiple
          and
        ></MySelect>
        <MySelect
          id="item"
          v-model:items="advancedControls.item.state"
          v-bind:options="options.item"
          label="Items"
          multiple
          and
        ></MySelect>
        <button
          class="button"
          style="margin-left: 2rem"
          v-on:click="refresh(true)"
        >
          Find builds
        </button>
      </div>
      <div v-show="buildCount !== null" class="build-count">
        Found {{ buildCount }} builds.
      </div>
      <div class="build-column">
        <MyBuild
          v-for="build in builds"
          v-bind:key="build.id"
          v-bind:data="build"
        ></MyBuild>
        <div ref="bottomElem">{{ bottomText }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import {
  SliderType,
  UnparsedBuild,
  UnparsedItem,
  Build,
  Item,
  BuildsResponse,
  Options,
  Nullable,
} from "./types";
import MyBuild from "./MyBuild.vue";
import MySelect from "./MySelect.vue";
import MySlider from "./MySlider.vue";
import emptyImageUrl from "/images/empty.png";

const fetchOrThrow = async (url: string) => {
  let response = await fetch(url);
  if (!response.ok) {
    throw Error(
      `HTTP error! Status: ${response.status} ${response.statusText}`
    );
  }
  return response;
};

const lastCheck = ref({ value: "loading ...", tooltip: "Loading .." });

(async () => {
  const lastCheckResponse = await fetchOrThrow("/api/last_check");
  lastCheck.value = await lastCheckResponse.json();
})();

const antiSpam = (
  "smi" +
  "te" +
  "bui" +
  "lds" +
  "pro" +
  "loki" +
  "gmail" +
  "." +
  "com"
).replace("loki", "@");

const getIsInBasicView = (searchParams: URLSearchParams) => {
  const view = searchParams.getAll("view");
  return !(view.length && view[view.length - 1] == "advanced");
};
const isInBasicView = ref(
  getIsInBasicView(new URL(window.location.href).searchParams)
);

const bottomElem = ref<HTMLElement | null>(null);
const bottomText = ref("Loading options ...");

const options = ref<Nullable<Options>>({
  season: null,
  league: null,
  phase: null,
  date: null,
  game_i: null,
  win: null,
  game_length: null,
  kda_ratio: null,
  kills: null,
  deaths: null,
  assists: null,
  role: null,
  team1: null,
  player1: null,
  god1: null,
  team2: null,
  player2: null,
  god2: null,
  relic: null,
  item: null,
});

const optionsFuture = (async (): Promise<Options> => {
  const optionsResponse = await fetchOrThrow("/api/options");
  return optionsResponse.json();
})();

onMounted(async () => {
  if (bottomElem.value === null) {
    throw Error("Illegal state");
  }

  try {
    options.value = await optionsFuture;
  } catch (e) {
    bottomText.value = "Failed to load options! Please try refreshing.";
    throw e;
  }

  // Wait for options to get initialized in child components.
  await nextTick();

  window.addEventListener("popstate", () => refresh(false));

  refresh(false);
});

interface Control {
  state: string[];
  readonly url?: string;
  readonly clientUrl?: string;
  readonly serverUrl?: string;
}

const basicControls = ref({
  god: { state: [], clientUrl: "god~", serverUrl: "god1" } as Control,
  role: { state: [], clientUrl: "role~" } as Control,
});

const advancedControls = ref({
  season: { state: [] } as Control,
  league: { state: [] } as Control,
  phase: { state: [] } as Control,
  date: { state: [] } as Control,
  gameI: { state: [], url: "game_i" } as Control,
  gameLength: { state: [], url: "game_length" } as Control,
  win: { state: [] } as Control,
  kdaRatio: { state: [], url: "kda_ratio" } as Control,
  kills: { state: [] } as Control,
  deaths: { state: [] } as Control,
  assists: { state: [] } as Control,
  role: { state: [] } as Control,
  team1: { state: [] } as Control,
  player1: { state: [] } as Control,
  god1: { state: [] } as Control,
  team2: { state: [] } as Control,
  player2: { state: [] } as Control,
  god2: { state: [] } as Control,
  relic: { state: [] } as Control,
  item: { state: [] } as Control,
});

const refresh = async (promptedByButtonClick: boolean) => {
  observer.disconnect();
  if (promptedByButtonClick) {
    controlsToClientUrl();
  } else {
    clientUrlToControls();
    // Wait for the controls to get validated in child components.
    await nextTick();
  }
  resetBuilds();
  controlsToBuildsSearchParams();
  updateBuilds();
};

const controlsToClientUrl = () => {
  let view: string;
  let controls: typeof basicControls | typeof advancedControls;
  if (isInBasicView.value) {
    view = "basic";
    controls = basicControls;
  } else {
    view = "advanced";
    controls = advancedControls;
  }

  const searchParams = new URLSearchParams({ view });

  for (const [controlId, control] of Object.entries(controls.value)) {
    const urlName = control.clientUrl ?? control.url ?? controlId;
    for (const value of control.state) {
      searchParams.append(urlName, value);
    }
  }

  history.pushState(undefined, "", "/?" + searchParams);
};

const clientUrlToControls = () => {
  const searchparams = new URL(window.location.href).searchParams;

  // When the URL changes with the next/prev button we need to reinitialize
  // few values (this is unnecessary on page load, but it is done anyway
  // to simplify code structure).
  isInBasicView.value = getIsInBasicView(searchparams);
  clearControls();

  for (const [controlId, control] of Object.entries(getCurrentControls())) {
    const urlName = control.clientUrl ?? control.url ?? controlId;
    const newState = searchparams.getAll(urlName);
    if (newState.length) {
      control.state = newState;
    }
  }
};

const builds = ref<Build[]>([]);
const buildCount = ref<number | null>(null);
let nextPage = 1;
let buildsSearchParams: URLSearchParams | null = null;

const resetBuilds = () => {
  builds.value = [];
  buildCount.value = null;
  nextPage = 1;
};

const controlsToBuildsSearchParams = () => {
  buildsSearchParams = new URLSearchParams();

  for (const [controlId, control] of Object.entries(getCurrentControls())) {
    const urlName = control.serverUrl ?? control.url ?? controlId;
    for (const value of control.state) {
      buildsSearchParams.append(urlName, value);
    }
  }
};

const updateBuilds = async () => {
  bottomText.value = "Loading builds ...";

  if (buildsSearchParams === null || bottomElem.value === null) {
    throw Error("Illegal state");
  }

  const url = `/api/builds?page=${nextPage}&` + buildsSearchParams;
  let buildsResponse: BuildsResponse;
  try {
    let response = await fetchOrThrow(url);
    buildsResponse = await response.json();
  } catch (e) {
    bottomText.value = "Failed to load builds! Please try refreshing.";
    throw e;
  }

  let unparsedBuilds: UnparsedBuild[];
  if ("count" in buildsResponse) {
    buildCount.value = buildsResponse.count;
    unparsedBuilds = buildsResponse.builds;
  } else {
    unparsedBuilds = buildsResponse;
  }

  const newBuilds = unparsedBuilds.map(
    (build): Build => ({
      ...build,
      relic1: handleImg(build.relic1),
      relic2: handleImg(build.relic2),
      item1: handleImg(build.item1),
      item2: handleImg(build.item2),
      item3: handleImg(build.item3),
      item4: handleImg(build.item4),
      item5: handleImg(build.item5),
      item6: handleImg(build.item6),
    })
  );

  if (newBuilds.length > 0) {
    nextPage += 1;
    builds.value.push(...newBuilds);
    bottomText.value = "";
    // Wait for the builds to get shown in child components.
    await nextTick();
    observer.observe(bottomElem.value);
  } else {
    bottomText.value = buildCount.value ? "End of list." : "";
  }
};

let observer = new IntersectionObserver((entries) => {
  // This function is called once immediately after observe is called,
  // even if the element is not intersecting,
  // so we need to check for it here.
  if (!entries[0].isIntersecting) {
    return;
  }
  observer.disconnect();
  updateBuilds();
});

const handleImg = (item: UnparsedItem): Item => {
  if (item) {
    if (item.image_data) {
      return {
        name: item.name,
        src: "data:image/png;base64," + item.image_data,
      };
    } else {
      return {
        name: item.name,
        src:
          "https://webcdn.hirezstudios.com/smite/item-icons/" + item.image_name,
      };
    }
  } else {
    return { name: "Empty", src: emptyImageUrl };
  }
};

const clearControls = () => {
  for (const control of Object.values(getCurrentControls())) {
    if (control.state.length) {
      control.state = [];
    }
  }
};

const getCurrentControls = () =>
  (isInBasicView.value ? basicControls : advancedControls).value;
</script>

<style>
.header-thing {
  /* section has 3rem padding, so this gives
  equal space above and below header-thing */
  margin-top: -0.67rem;
  margin-bottom: 2.34rem;
  display: flex;
  flex-direction: column;
  row-gap: 0.667rem;
}
.update-info {
  text-align: center;
}
.contact-info {
  text-align: center;
}
@media screen and (min-width: 750px) {
  .header-thing {
    flex-direction: row;
    justify-content: space-between;
    align-items: flex-end;
  }
  .update-info {
    text-align: left;
  }
  .contact-info {
    text-align: right;
  }
}
@media screen and (min-width: 1216px) {
  .header-thing {
    margin-top: -2.667rem;
    margin-bottom: 0rem;
  }
  /* These children elements are moved instead of the whole header-thing,
  because otherwise either the links or the tabs are not clickable due to
  the containers being on top of each other*/
  .update-info {
    position: relative;
    top: 2.667rem;
  }
  .contact-info {
    position: relative;
    top: 2.667rem;
  }
}
.select-row {
  display: flex;
  column-gap: 1.333rem;
  row-gap: 1.333rem;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  margin-bottom: 1rem;
}
.build-column {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.build-count {
  text-align: center;
  margin-bottom: 1rem;
}
.ts-wrapper.multi .ts-control > div {
  margin: 0 5px 0 0;
  padding: 0 5px;
}
.ts-wrapper.plugin-remove_button .item .remove {
  padding: 0 5px;
}
#basic-row .ts-control {
  min-width: 11rem;
}
#advanced-row .ts-control {
  min-width: 9rem;
}
#basic-row input {
  min-width: unset;
}
#advanced-row input {
  min-width: 2.2rem;
}
/* https://refreshless.com/nouislider/examples/#section-styling */
.slider-styled,
.slider-styled .noUi-handle {
  box-shadow: none;
}
.slider-styled .noUi-handle::before,
.slider-styled .noUi-handle::after {
  display: none;
}
.slider-styled .noUi-handle .noUi-touch-area {
  border: 1px solid transparent;
  position: absolute;
  top: -10px;
  left: -10px;
  right: -10px;
  bottom: -10px;
  width: auto;
  height: auto;
}
.slider-styled {
  height: 10px;
}
.slider-styled .noUi-connect {
  background: #01abc9;
}
.slider-styled .noUi-handle {
  height: 18px;
  width: 18px;
  top: -5px;
  right: -9px; /* half the width */
  border-radius: 9px;
}
</style>
