<template>
  <div class="section">
    <div class="container">
      <div class="tabs is-centered is-medium is-boxed">
        <ul>
          <li class="is-active"><a>Basic search</a></li>
          <li><a><s>Advanced search</s></a></li>
        </ul>
      </div>
      <div class="has-text-centered">
        <label for="roles">God: </label>
        <select class="select" id="gods">
          <option v-for="god in god1s" v-bind:key="god">
            {{ god }}
          </option>
        </select>
        <label for="roles">Role: </label>
        <select class="select" id="roles">
          <option v-for="role in roles" v-bind:key="role">
            {{ role }}
          </option>
        </select>
        <button class="button">Find builds</button>
      </div>
      <ul class="has-text-centered">
        <li v-for="build in builds" v-bind:key="build.id">
          {{ build.season }} {{ build.league }} {{ build.phase }}
          {{ build.date }} {{ build.role }}
          {{ build.game_i }} {{ build.win }} {{ build.game_length }}
          {{ build.kills }} {{ build.deaths }} {{ build.assists }}
          {{ build.team1 }} {{ build.player1 }} {{ build.god1 }}
          {{ build.team2 }} {{ build.player2 }} {{ build.god2 }}
          {{ build.relic1 }} {{ build.relic2 }}
          {{ build.item1 }} {{ build.item2 }} {{build.item3 }}
          {{ build.item4 }} {{ build.item5 }} {{build.item6 }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
  export default {
    data() {
      return {
        backend: import.meta.env.PROD ? 'https://gebgebgeb.pythonanywhere.com' : 'http://localhost:8080',
        god1s: ['Loading ...'],
        roles: ['Loading ...'],
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
      get_select_options() {
        fetch(`${this.backend}/select_options`)
        .then(response => response.json())
        .then(json => {
          this.god1s = json['god1s']
          this.roles = json['roles']
          })
        .catch(error => console.log(error))
      },
      get_builds() {
        fetch(`${this.backend}/builds`)
        .then(response => response.json())
        .then(json => this.builds = json)
        .catch(error => console.log(error))
      }
    },

    mounted() {
      this.get_select_options()
      this.get_builds()
    }
  }
</script>

<style>
</style>
