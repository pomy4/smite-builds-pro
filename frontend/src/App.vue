<template>
  <div class="section">
    <div class="container">
      <div class="tabs is-centered is-medium is-boxed">
        <ul>
          <li class="is-active"><a>Basic search</a></li>
          <li><a><s>Advanced search</s></a></li>
        </ul>
      </div>
      <div class="columns is-mobile is-centered is-multiline">
        <div class="column is-narrow">
          <div class="field is-horizontal">
            <div class="field-label is-normal">
              <label class="label">God</label>
            </div>
            <div class="field-body">
              <div class="control">
                <div class="select">
                  <select id="god1s">
                    <option v-for="god1 in god1s" v-bind:key="god1" v-bind:value="god1">
                      {{ god1 }}
                    </option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="column is-narrow">
          <div class="field is-horizontal">
            <div class="field-label is-normal">
              <label class="label">Role</label>
            </div>
            <div class="field-body">
              <div class="control">
                <div class="select">
                  <select id="roles">
                    <option v-for="role in roles" v-bind:key="role" v-bind:value="role">
                      {{ role }}
                    </option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="column is-narrow">
          <div class="field">
            <div class="control">
              <button class="button" v-on:click="get_builds">Find builds</button>
            </div>
          </div>
        </div>
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
      async get_builds() {
        let god1 = document.getElementById('god1s').value
        let role = document.getElementById('roles').value
        let url = `${this.backend}/builds?god1=${god1}&role=${role}`
        let response = await fetch(url)
        if (! response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`)
        }
        this.builds = await response.json()
      },
      async get_select_options() {
        let url = `${this.backend}/select_options`
        let response = await fetch(url)
        if (! response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`)
        }
        let json = await response.json()
        this.god1s = json['god1s']
        this.roles = json['roles']
      }
    },

    mounted() {
      this.get_select_options()
    }
  }
</script>

<style>
</style>
