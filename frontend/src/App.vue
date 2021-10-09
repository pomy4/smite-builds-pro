<template>
  <div class="section">
    <div class="container">
      <div class="tabs is-centered is-medium is-boxed">
        <ul>
          <li v-on:click="is_in_basic_view=true"  v-bind:class="{ 'is-active':  is_in_basic_view }"><a>Basic search</a></li>
          <li v-on:click="is_in_basic_view=false" v-bind:class="{ 'is-active': !is_in_basic_view }"><a>Advanced search</a></li>
        </ul>
      </div>
      <div v-show="is_in_basic_view" class="select-row" id="basic-row">
        <label-select label="God"  id="god1"></label-select>
        <label-select label="Role" id="role"></label-select>
        <button class="button" style="margin-left: 2rem" v-on:click="refresh(true)">Find builds</button>
      </div>
      <div v-show="!is_in_basic_view" class="select-row" id="advanced-row">
        <button class="button" style="margin-right: 2rem" v-on:click="clear_all_button">Clear all</button>
        <!-- <label-select label="Seasons"  id="seasons" multiple></label-select>
        <label-select label="Leagues"  id="leagues" multiple></label-select> -->
        <label-select label="Phases"  id="phases" multiple></label-select>
        <label-select label="Win" id="wins" multiple></label-select>
        <label-select label="Roles" id="roles" multiple></label-select>
        <label-select label="Teams" id="team1s" multiple></label-select>
        <label-select label="Players" id="player1s" multiple></label-select>
        <label-select label="Gods"  id="god1s" multiple></label-select>
        <label-select label="Opponent teams" id="team2s" multiple></label-select>
        <label-select label="Opponent players" id="player2s" multiple></label-select>
        <label-select label="Opponent gods"  id="god2s" multiple></label-select>
        <label-select label="Relics" id="relics" multiple and></label-select>
        <label-select label="Items"  id="items" multiple and></label-select>
        <button class="button" style="margin-left: 2rem" v-on:click="refresh(true)">Find builds</button>
      </div>
      <div v-show="build_count !== null" class="build-count">Found {{ build_count }} builds.</div>
      <div class="build-column">
        <build v-for="build in builds" v-bind:key="build.id" v-bind:data="build"></build>
        <div id="bottom-of-page"></div>
      </div>
    </div>
  </div>
</template>

<script>
  import Build from './Build.vue'
  import LabelSelect from './LabelSelect.vue'
  import empty_url from '/images/empty.png'
  import { SelectJsSingle, SelectJsMultiple } from './Controls.js'

  export default {
    components: {
      'build': Build,
        LabelSelect
    },
    data() {
      return {
        is_in_basic_view: true,
        builds: [],
        build_count: null,
      }
    },
    methods: {
      clear_all_button() {
        for (const control of Object.values(this.controls)) {
          control.clear()
        }
      },
      refresh(prompted_by_button_click) {
        clearTimeout(this.watch_for_intersections_timeout)
        this.watch_for_intersections = false
        if (prompted_by_button_click) {
          this.controls_to_filters_and_client_url()
        } else {
          this.client_url_to_controls_and_filters()
        }
        this.reset_builds()
        this.get_builds()
      },
      reset_builds() {
        this.builds = []
        this.build_count = null
        this.page = 1
        this.is_on_last_page = false
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
        if (this.page === 1) {
          this.build_count = builds['count']
          builds = builds['builds']
        }
        for (let build of builds) {
          build.relic1 = this.handle_img(build.relic1)
          build.relic2 = this.handle_img(build.relic2)
          build.item1 = this.handle_img(build.item1)
          build.item2 = this.handle_img(build.item2)
          build.item3 = this.handle_img(build.item3)
          build.item4 = this.handle_img(build.item4)
          build.item5 = this.handle_img(build.item5)
          build.item6 = this.handle_img(build.item6)
        }
        if (builds.length > 0) {
          this.builds.push(...builds)
          this.page += 1
        }
        else {
          this.is_on_last_page = true
        }
        bottom_of_page.textContent = ''
        this.start_watching_in_the_future()
      },
      filters_to_server_url_fragment() {
        let url = `?page=${this.page}`
        if (this.is_next_search_basic) {
          if (this.filter_basic_god1) {
            url += `&god1=${this.filter_basic_god1}`
          }
          if (this.filter_basic_role) {
            url += `&role=${this.filter_basic_role}`
          }
        } else {
          for (const [key, vals] of Object.entries(this.filters)) {
            for (const val of vals) {
              url += `&${key.slice(0, -1)}=${val}`
            }
          }
        }
        return url
      },
      handle_img(item) {
        if (item) {
          return {'name': item.name, 'src': 'https://webcdn.hirezstudios.com/smite/item-icons/' + item.image_name}
        } else {
          return {'name': 'Empty', 'src': empty_url}
        }
      },
      start_watching_in_the_future() {
        this.watch_for_intersections_timeout = setTimeout(()=>
          this.watch_for_intersections=true, 50)
      },
      controls_to_filters_and_client_url() {
        this.filter_basic_god1 = undefined
        this.filter_basic_role = undefined
        this.filters = {}

        let url_fragment = '?view='
        if (this.is_in_basic_view) {
          url_fragment += 'basic'
          this.is_next_search_basic = true
        } else {
          url_fragment += 'advanced'
          this.is_next_search_basic = false
        }

        const basic_god1 = this.select_basic_god1.get()
        if (basic_god1) {
          url_fragment += `&god1~=${basic_god1}`
          this.filter_basic_god1 = basic_god1
        }
        const basic_role = this.select_basic_role.get()
        if (basic_role) {
          url_fragment += `&role~=${basic_role}`
          this.filter_basic_role = basic_role
        }

        for (const [keys, control] of Object.entries(this.controls)) {
          const vals = control.get()
          for (const val of vals) {
            url_fragment += `&${keys.slice(0, -1)}=${val}`
          }
          if (vals.length > 0) {
            this.filters[keys] = vals
          }
        }

        let url_object = new URL(url_fragment, window.location.origin)
        history.pushState(undefined, '' , url_object.href)
      },
      client_url_to_controls_and_filters() {
        this.select_basic_god1.clear()
        this.select_basic_role.clear()
        this.filter_basic_god1 = undefined
        this.filter_basic_role = undefined
        for (const control of Object.values(this.controls)) {
          control.clear()
        }
        this.filters = {}

        let search_params = new URL(window.location.href).searchParams
        if (search_params.get('view') !== 'advanced') {
          this.is_in_basic_view = true
          this.is_next_search_basic = true
        } else {
          this.is_in_basic_view = false
          this.is_next_search_basic = false
        }
        search_params.delete('view')

        const basic_god1 = search_params.get('god1~')
        if (basic_god1) {
          this.select_basic_god1.add(basic_god1)
          this.filter_basic_god1 = basic_god1
        }
        search_params.delete('god1~')
        const basic_role = search_params.get('role~')
        if (basic_role) {
          this.select_basic_role.add(basic_role)
          this.filter_basic_role1 = basic_role
        }
        search_params.delete('role~')

        for (const key of search_params.keys()) {
          const keys = `${key}s`
          if (this.controls[keys]) {
            const vals = search_params.getAll(key)
            this.controls[keys].add(vals)
            this.filters[keys] = vals
          }
        }
      },
      async get_options() {
        let response = await fetch('/api/options')
        if (! response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`)
        }
        return await response.json()
      },
    },
    async mounted() {
      let options_future = this.get_options()

      // Construction.
      this.select_basic_god1 = new SelectJsSingle('god1')
      this.select_basic_role = new SelectJsSingle('role')
      this.controls = {}
      const nodes = document.querySelectorAll('#advanced-row select')
      for (const node of nodes) {
        this.controls[node.id] = new SelectJsMultiple(node)
      }

      // Initialization.
      const options = await options_future
      this.select_basic_god1.init(options['god1s'])
      this.select_basic_role.init(options['roles'])
      for (const node of nodes) {
        this.controls[node.id].init(options[node.id])
      }

      // Pagination.
      let observer = new IntersectionObserver(()=> {
        if (this.watch_for_intersections && ! this.is_on_last_page) {
          this.watch_for_intersections = false
          this.get_builds()
        }
      })
      observer.observe(document.getElementById('bottom-of-page'))

      // History/navigation.
      window.addEventListener('popstate', () => {
        this.refresh(false)
      })

      this.refresh(false)
    }
  }
</script>

<style>
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
</style>
