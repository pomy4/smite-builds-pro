<template>
  <div class="build-row block box">
    <!--<div class="metadata-row">-->
      <div class="my-column" style="width: 8.333rem">
        <span><span>Season </span><span>{{ data.season }}</span></span>
        <span><span>{{ data.league }}</span></span>
        <span><span>{{ data.phase }}</span></span>
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
      <div class="my-column" style="width: 4rem">
        <span>{{ data.player1 }}</span>
        <span>{{ data.role }}</span>
        <span>{{ data.kills }}/{{ data.deaths }}/{{ data.assists }}</span>
      </div>
      <div class="my-column" style="width: 5.667rem">
        <span>{{ data.god1 }}</span>
      </div>
    <!--</div>-->
    <!--<div class="data-row">-->
      <div class="item-row">
        <div class="my-column">
          <img v-bind:src="data.relic1.src" v-bind:alt="data.relic1.name" v-bind:title="data.relic1.name">
        </div>
        <div class="my-column">
          <img v-bind:src="data.relic2.src" v-bind:alt="data.relic2.name" v-bind:title="data.relic2.name">
        </div>
      </div>
      <div class="item-row">
        <div class="my-column">
          <img v-bind:src="data.item1.src" v-bind:alt="data.item1.name" v-bind:title="data.item1.name">
        </div>
        <div class="my-column">
          <img v-bind:src="data.item2.src" v-bind:alt="data.item2.name" v-bind:title="data.item2.name">
        </div>
        <div class="my-column">
          <img v-bind:src="data.item3.src" v-bind:alt="data.item3.name" v-bind:title="data.item3.name">
        </div>
        <div class="my-column">
          <img v-bind:src="data.item4.src" v-bind:alt="data.item4.name" v-bind:title="data.item4.name">
        </div>
        <div class="my-column">
          <img v-bind:src="data.item5.src" v-bind:alt="data.item5.name" v-bind:title="data.item5.name">
        </div>
        <div class="my-column">
          <img v-bind:src="data.item6.src" v-bind:alt="data.item6.name" v-bind:title="data.item6.name">
        </div>
      </div>
    <!--</div>-->
    <div class="my-column" style="width: 6.667rem">
      <span>Opponent:</span>
      <span>{{ data.god2 }}</span>
      <span>{{ data.player2 }}</span>
    </div>
  </div>
</template>

<script>
export default {
  props: ['data']
}
</script>

<style>
.build-row {
  display: inline-flex;
  column-gap: 0.667rem;
  row-gap: 1.333rem;
  flex-wrap: wrap;
  justify-content: center;
}
.metadata-row {
  display: flex;
}
.data-row {
  display: flex;
  column-gap: 1.333rem;
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
