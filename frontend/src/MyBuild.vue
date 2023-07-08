<template>
  <div class="build-row block box">
    <div class="my-column" style="width: 12rem">
      <span
        ><span>Season </span><span>{{ data.season }}</span></span
      >
      <span
        ><span>{{ data.league }}</span></span
      >
      <span
        ><span>{{ data.phase }}</span></span
      >
    </div>
    <div class="my-column" style="width: 6.667rem">
      <span>{{ data.date }}</span>
      <span>{{ data.team1 }} VS {{ data.team2 }}</span>
      <a v-bind:href="data.match_url">Link to match</a>
    </div>
    <div class="my-column" style="width: 6.667rem">
      <span>Game #{{ data.game_i }}</span>
      <span>{{ data.game_length }}</span>
      <span v-if="data.win">WIN</span><span v-else>LOSE</span>
    </div>
    <div class="my-column" style="width: 4.667rem">
      <span>{{ data.player1 }}</span>
      <span>{{ data.role }}</span>
      <span
        >{{ data.kills }}/{{ data.deaths }}/{{ data.assists }} ({{
          data.kda_ratio
        }})</span
      >
    </div>
    <div class="my-column" style="width: 5.667rem">
      <span>{{ data.god1 }}</span>
    </div>
    <div class="item-row">
      <div class="my-column">
        <img
          v-bind:src="data.relics[0].src"
          v-bind:alt="data.relics[0].name"
          v-bind:title="data.relics[0].name"
        />
      </div>
      <div class="my-column">
        <img
          v-bind:src="data.relics[1].src"
          v-bind:alt="data.relics[1].name"
          v-bind:title="data.relics[1].name"
        />
      </div>
    </div>
    <div class="item-row">
      <div class="my-column">
        <img
          v-bind:src="data.items[0].src"
          v-bind:alt="data.items[0].name"
          v-bind:title="data.items[0].name"
        />
      </div>
      <div class="my-column">
        <img
          v-bind:src="data.items[1].src"
          v-bind:alt="data.items[1].name"
          v-bind:title="data.items[1].name"
        />
      </div>
      <div class="my-column">
        <img
          v-bind:src="data.items[2].src"
          v-bind:alt="data.items[1].name"
          v-bind:title="data.items[1].name"
        />
      </div>
      <div class="my-column">
        <img
          v-bind:src="data.items[3].src"
          v-bind:alt="data.items[3].name"
          v-bind:title="data.items[3].name"
        />
      </div>
      <div class="my-column">
        <img
          v-bind:src="data.items[4].src"
          v-bind:alt="data.items[4].name"
          v-bind:title="data.items[4].name"
        />
      </div>
      <div class="my-column">
        <img
          v-bind:src="data.items[5].src"
          v-bind:alt="data.items[5].name"
          v-bind:title="data.items[5].name"
        />
      </div>
    </div>
    <div class="my-column" style="width: 6.667rem">
      <span>Opponent:</span>
      <span>{{ data.god2 }}</span>
      <span>{{ data.player2 }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Build } from "./types";
defineProps<{ data: Build }>();
</script>

<style>
.build-row {
  display: inline-flex;
  column-gap: 0.667rem;
  row-gap: 1.333rem;
  flex-wrap: wrap;
  justify-content: center;
}
.item-row {
  display: flex;
  column-gap: 0.333rem;
}
.my-column {
  white-space: nowrap;
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
  row-gap: 0.333rem;
}
img {
  width: 3.333rem;
  max-width: none;
}
</style>
