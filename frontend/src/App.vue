<template>
  <div class="section">
    <div class="container">
      <div class="tabs is-centered is-medium is-boxed">
        <ul>
          <li class="is-active"><a>Basic search</a></li>
          <li><a><s>Advanced search</s></a></li>
        </ul>
      </div>
      <div class="select-row">
        <div>
          <div class="label-select">
            <label class="label">God</label>
            <select id="god1s" autocomplete="on" multiple></select>
          </div>
        </div>
        <div>
          <div class="label-select">
            <label class="label">Role</label>
            <select id="roles" autocomplete="on" multiple>
            </select>
          </div>
        </div>
        <button class="button" style="margin-left: 2rem" v-on:click="get_builds">Find builds</button>
      </div>
      <div class="build-column">
        <build v-for="build in builds" v-bind:key="build.id" v-bind:data="build"></build>
      </div>
    </div>
  </div>
</template>

<script>
  import Build from './Build.vue'

  export default {
    components: {
      'build': Build
    },
    data() {
      return {
        god1s: undefined,
        roles: undefined,
        builds: []
      }
    },
    methods: {
      set_default_img_if_undefined(item) {
        if (item) {
          return {'src': 'https://webcdn.hirezstudios.com/smite/item-icons/' + item.short, 'name': item.long}
        } else {
          return {'src': 'data:image/gif;base64,R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs=', 'name': 'Empty'}
        }
      },
      async get_builds() {
        let god1s = this.god1s.getValue()
        let roles = this.roles.getValue()
        let url = '/api/builds?'
        for (let god1 of god1s) {
          url += `god1=${god1}&`
        }
        for (let role of roles) {
          url += `role=${role}&`
        }
        let response = await fetch(url)
        if (! response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`)
        }
        let builds = await response.json()
        for (let build of builds) {
          build.relic1 = this.set_default_img_if_undefined(build.relic1)
          build.relic2 = this.set_default_img_if_undefined(build.relic2)
          build.item1 = this.set_default_img_if_undefined(build.item1)
          build.item2 = this.set_default_img_if_undefined(build.item2)
          build.item3 = this.set_default_img_if_undefined(build.item3)
          build.item4 = this.set_default_img_if_undefined(build.item4)
          build.item5 = this.set_default_img_if_undefined(build.item5)
          build.item6 = this.set_default_img_if_undefined(build.item6)
        }
        this.builds = builds
      },
      async get_select_options() {
        let response = await fetch('/api/select_options')
        if (! response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`)
        }
        return await response.json()
      },
      create_select(name) {
        return new TomSelect(`#${name}`, {
          options: [{value: 1, text: 'Loading ...', disabled: true}],
          placeholder: 'All',
          hidePlaceholder: true,
          // eslint-disable-next-line no-unused-vars
          onItemAdd: function(_0, _1) {
            this.setTextboxValue('')
            this.refreshOptions(false)
          }
        })
      },
      update_select(select, options) {
        options = options.map(option => {return {value: option, text: option}})
        select.removeOption(1)
        select.addOptions(options)
        select.refreshOptions(false)
      }
    },
    async mounted() {
      this.god1s = this.create_select('god1s')
      this.roles = this.create_select('roles')
      let options = await this.get_select_options()
      this.update_select(this.god1s, options['god1s'])
      this.update_select(this.roles, options['roles'])
      await this.get_builds()
    }
  }
</script>

<style>
.input-hidden .ts-control > input {
  opacity: 0;
  position: unset;
  left: unset;
  min-width: 5rem;
}
.ts-control > input {
  min-width: 5rem;
}
.label:not(:last-child) {
  margin-bottom: unset;
}
.label-select {
  display: flex;
  align-items: center;
  column-gap: 0.667rem;
}
.select-row {
  display: flex;
  column-gap: 1.333rem;
  row-gap: 1.333rem;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  margin-bottom: 1.333rem;
}
.build-column {
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
