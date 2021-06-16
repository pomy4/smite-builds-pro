<template>
  <div>
    <label for="players">Choose a player:</label>
    <select v-on:change="choose_player" id="players">
      <option v-for="player in players" :value="player">
        {{ player }}
      </option>
    </select>
    <ul>
      <li v-for="build in builds">
        {{ build.player }} {{ build.role }} {{ build.god }}
      </li>
    </ul>
  </div>
</template>

<script>
  export default {
    data() {
      return {
        backend: import.meta.env.PROD ? 'https://gebgebgeb.pythonanywhere.com' : 'http://localhost:8080',
        players: [],
        builds: []
      }
    },

    methods: {
      choose_player(event) {
        fetch(`${this.backend}/player/${event.target.value}`)
        .then(response => response.json())
        .then(json => this.builds = json)
        .catch(error => console.log(error))
      },
      populate_select() {
        fetch(`${this.backend}/players`)
        .then(response => response.json())
        .then(json => this.players = json)
        .catch(error => console.log(error))
      }
    },

    mounted() {
      this.populate_select()
    }
  }
</script>

<style>
</style>
