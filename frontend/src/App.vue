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
        builds: [],
        page: 1,
        watch_for_intersections: false,
        watch_for_intersections_timeout: undefined,
        selects: {},
        filters: {},
        translations: {'god1s': 'God', 'roles': 'Role'}, // This will be used for printing.
        // This will be used in the basic view.
        select_god1: undefined,
        select_role: undefined,
        filter_god1: [],
        filter_role: [],
      }
    },
    methods: {
      button_clicked() {
        clearTimeout(this.watch_for_intersections_timeout)
        this.watch_for_intersections = false
        this.selects_to_filters_and_client_url()
        this.reset_builds()
        this.get_builds()
      },
      reset_builds() {
        this.builds = []
        this.page = 1
      },
      async get_builds() {
        let bottom_of_page = document.getElementById('bottom-of-page')
        bottom_of_page.textContent = 'Loading builds ...'
        let url = `/api/builds${this.filters_to_server_url_fragment()}`
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
      filters_to_server_url_fragment() {
        let url = `?page=${this.page}`
        for (const [key, vals] of Object.entries(this.filters)) {
          for (const val of vals) {
            url += `&${key.slice(0, -1)}=${val}`
          }
        }
        return url
      },
      set_default_img_if_undefined(item) {
        if (item) {
          return {'src': 'https://webcdn.hirezstudios.com/smite/item-icons/' + item.short, 'name': item.long}
        } else {
          return {'src': 'data:image/gif;base64,R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs=', 'name': 'Empty'}
        }
      },
      start_watching_in_the_future() {
        this.watch_for_intersections_timeout = setTimeout(()=>
          this.watch_for_intersections=true, 50)
      },
      selects_to_filters_and_client_url() {
        let url_fragment = `?view=basic`
        for (const [keys, select] of Object.entries(this.selects)) {
          const vals = select.getValue()
          this.filters[keys] = vals
          for (const val of vals) {
            url_fragment += `&${keys.slice(0, -1)}=${val}`
          }
        }
        let url_object = new URL(url_fragment, window.location.origin)
        history.pushState(undefined, '' , url_object.href)
      },
      client_url_to_filters_and_selects() {
        this.filters = {}
        for (const select of Object.values(this.selects)) {
          select.clear()
        }
        let search_params = new URL(window.location.href).searchParams
        for (const key of search_params.keys()) {
          console.log(key)
          if (key == 'view') {
            continue // TODO
          }
          const keys = `${key}s`
          const vals = search_params.getAll(key)
          this.filters[keys] = vals
          for (const val of vals) {
            this.selects[keys].addItem(val)
          }
        }
        // TODO print selected filters
      },
      // These functions are called only on page load.
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
    },
    async mounted() {
      let options = await this.get_select_options()
      // Create Tom-selects.
      for (const node of document.querySelectorAll("select")) {
        const id = node.id
        this.selects[id] = this.create_select(id)
        this.update_select(this.selects[id], options[id])
      }
      // Prepare pagination.
      let observer = new IntersectionObserver(()=> {
        if (this.watch_for_intersections) {
          this.watch_for_intersections = false
          this.get_builds()
        }
      })
      observer.observe(document.getElementById('bottom-of-page'))
      // Prepare navigation.
      window.addEventListener('popstate', () => {
        clearTimeout(this.watch_for_intersections_timeout)
        this.watch_for_intersections = false
        // Same as button_clicked except for this line.
        this.client_url_to_filters_and_selects()
        this.reset_builds()
        this.get_builds()
      })

      this.client_url_to_filters_and_selects()
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
