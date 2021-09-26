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
        <div>
          <div class="label-select">
            <label class="label">God</label>
            <select id="god1" autocomplete="on"></select>
          </div>
        </div>
        <div>
          <div class="label-select">
            <label class="label">Role</label>
            <select id="role" autocomplete="on">
            </select>
          </div>
        </div>
        <button class="button" style="margin-left: 2rem" v-on:click="button_clicked">Find builds</button>
      </div>
      <div v-show="!is_in_basic_view" class="select-row" id="advanced-row">
        <div>
          <div class="label-select">
            <label class="label">God(s)</label>
            <select id="god1s" autocomplete="on" multiple></select>
          </div>
        </div>
        <div>
          <div class="label-select">
            <label class="label">Role(s)</label>
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
        is_on_last_page: false,
        is_in_basic_view: true,
        is_next_search_basic: true,
        watch_for_intersections: false,
        watch_for_intersections_timeout: undefined,
        selects: {},
        filters: {},
        translations: {'god1s': 'God', 'roles': 'Role'}, // This will be used for printing.
        // This will be used in the basic view.
        select_basic_god1: undefined,
        select_basic_role: undefined,
        filter_basic_god1: undefined,
        filter_basic_role: undefined,
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

        const basic_god1 = this.select_basic_god1.getValue()
        if (basic_god1) {
          url_fragment += `&god1~=${basic_god1}`
          this.filter_basic_god1 = basic_god1
        }
        const basic_role = this.select_basic_role.getValue()
        if (basic_role) {
          url_fragment += `&role~=${basic_role}`
          this.filter_basic_role = basic_role
        }

        for (const [keys, select] of Object.entries(this.selects)) {
          const vals = select.getValue()
          for (const val of vals) {
            url_fragment += `&${keys.slice(0, -1)}=${val}`
          }
          this.filters[keys] = vals
        }

        let url_object = new URL(url_fragment, window.location.origin)
        history.pushState(undefined, '' , url_object.href)
      },
      client_url_to_selects_and_filters() {
        this.select_basic_god1.clear()
        this.select_basic_role.clear()
        this.filter_basic_god1 = undefined
        this.filter_basic_role = undefined
        for (const select of Object.values(this.selects)) {
          select.clear()
        }
        this.filters = {}

        let search_params = new URL(window.location.href).searchParams
        if (search_params.get('view') != 'advanced') {
          this.is_in_basic_view = true
          this.is_next_search_basic = true
        } else {
          this.is_in_basic_view = false
          this.is_next_search_basic = false
        }
        search_params.delete('view')

        const basic_god1 = search_params.get('god1~')
        if (basic_god1) {
          this.select_basic_god1.addItem(basic_god1)
          this.filter_basic_god1 = basic_god1
        }
        search_params.delete('god1~')
        const basic_role = search_params.get('role1~')
        if (basic_role) {
          this.select_basic_role.addItem(basic_role)
          this.filter_basic_role1 = basic_role
        }
        search_params.delete('role1~')

        for (const key of search_params.keys()) {
          const keys = `${key}s`
          const vals = search_params.getAll(key)
          for (const val of vals) {
            this.selects[keys].addItem(val)
          }
          this.filters[keys] = vals
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
      create_select(id) {
        return new TomSelect(`#${id}`, {
          options: [{value: 1, text: 'Loading ...', disabled: true}],
          placeholder: 'All',
          hidePlaceholder: false,
          plugins: ['no_active_items', 'remove_button', 'caret_position', 'clear_button'],
          maxOptions: 999,
          // eslint-disable-next-line no-unused-vars
          onItemAdd: function(_0, _1) {
            this.settings.placeholder = 'or ...'
            this.setTextboxValue('')
            this.refreshOptions(false)
          },
          // eslint-disable-next-line no-unused-vars
          onItemRemove: function(_) {
            if (this.getValue().length == 0) {
              document.getElementById(`${id}-ts-control`).setAttribute('placeholder', 'All')
            }
          }
        })
      },
      create_select_single(id) {
        return new TomSelect(`#${id}`, {
          options: [{value: 1, text: 'Loading ...', disabled: true}],
          placeholder: 'All',
          hidePlaceholder: true,
          plugins: ['no_active_items', 'remove_button'],
          maxOptions: 999,
          // eslint-disable-next-line no-unused-vars
          onItemRemove: function(_) {
            if (this.getValue().length == 0) {
              document.getElementById(`${id}-ts-control`).setAttribute('placeholder', 'All')
              // or this.settings.placeholder = 'All' + this.inputState()
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
      this.select_basic_god1 = this.create_select_single('god1')
      this.update_select(this.select_basic_god1, options['god1s'])
      this.select_basic_role = this.create_select_single('role')
      this.update_select(this.select_basic_role, options['roles'])
      for (const node of document.querySelectorAll('#advanced-row select')) {
        const id = node.id
        this.selects[id] = this.create_select(id)
        this.update_select(this.selects[id], options[id])
      }
      // Prepare pagination.
      let observer = new IntersectionObserver(()=> {
        if (this.watch_for_intersections && ! this.is_on_last_page) {
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
        this.client_url_to_selects_and_filters()
        this.reset_builds()
        this.get_builds()
      })

      this.client_url_to_selects_and_filters()
      this.get_builds()
    }
  }
</script>

<style>
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
.ts-wrapper.plugin-remove_button .item .remove {
  padding: 0 5px;
}
.ts-control {
  min-width: 10rem;
}
#basic-row input {
  min-width: unset;
}
#advanced-row input {
  min-width: 2rem;
}
</style>
