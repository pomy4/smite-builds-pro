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
        <button class="button" style="margin-left: 2rem" v-on:click="button_clicked">Find builds</button>
      </div>
      <div class="build-column">
        <build v-for="build in builds" v-bind:key="build.id" v-bind:data="build"></build>
        <div id="bottom-of-page"></div>
      </div>
    </div>
  </div>
</template>

<script>
  import Build from './Build.vue'
  import TomSelect from 'tom-select'
  import 'tom-select/dist/css/tom-select.css'

  export default {
    components: {
      'build': Build
    },
    data() {
      return {
        select_god1s: undefined,
        select_roles: undefined,
        filters_god1s: [],
        filters_roles: [],
        builds: [],
        page: 1,
        watch_for_intersections: false,
        watch_for_intersections_timeout: undefined,
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
      button_clicked() {
        clearTimeout(this.watch_for_intersections_timeout)
        this.watch_for_intersections = false
        this.update_filters()
        this.reset_builds()
        this.get_builds()
      },
      update_filters() {
        this.filters_god1s = this.select_god1s.getValue()
        this.filters_roles = this.select_roles.getValue()
      },
      reset_builds() {
        this.builds = []
        this.page = 1
      },
      async get_builds() {
        let bottom_of_page = document.getElementById('bottom-of-page')
        bottom_of_page.textContent = 'Loading builds ...'
        let url = `/api/builds?page=${this.page}`
        for (let god1 of this.filters_god1s) {
          url += `&god1=${god1}`
        }
        for (let role of this.filters_roles) {
          url += `&role=${role}`
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
        this.builds.push(...builds)
        this.page += 1
        bottom_of_page.textContent = ''
        this.start_watching_in_the_future()
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
          hidePlaceholder: false,
          plugins: ['caret_position', 'clear_button', 'no_active_items', 'remove_button'],
          // eslint-disable-next-line no-unused-vars
          onItemAdd: function(_0, _1) {
            this.setTextboxValue('')
            this.refreshOptions(false)
            this.settings.placeholder = 'or ...'
          },
          // eslint-disable-next-line no-unused-vars
          onItemRemove: function(_) {
            if (this.getValue().length == 0) {
              this.settings.placeholder = 'All'
            }
          }
        })
      },
      update_select(select, options) {
        options = options.map(option => {return {value: option, text: option}})
        select.removeOption(1)
        select.addOptions(options)
        select.refreshOptions(false)
      },
      start_watching_in_the_future() {
        this.watch_for_intersections_timeout = setTimeout(()=>
          this.watch_for_intersections=true, 50)
      }
    },
    async mounted() {
      this.select_god1s = this.create_select('god1s')
      this.select_roles = this.create_select('roles')
      let options = await this.get_select_options()
      this.update_select(this.select_god1s, options['god1s'])
      this.update_select(this.select_roles, options['roles'])
      let observer = new IntersectionObserver(()=> {
        if (this.watch_for_intersections) {
          this.watch_for_intersections = false
          this.get_builds()
        }
      })
      observer.observe(document.getElementById('bottom-of-page'))
      this.get_builds()
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
.ts-wrapper.multi .ts-control > div {
  margin: 0 5px 0 0;
  padding: 0 5px;
}
</style>
