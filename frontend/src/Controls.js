import TomSelect from 'tom-select'
import 'tom-select/dist/css/tom-select.css'

class SelectJs {
  init(options) {
    options = options.map(option => {return {value: option, text: option}})
    this.tom.removeOption(1)
    this.tom.addOptions(options)
    this.tom.refreshOptions(false)
  }
  clear() {
    this.tom.clear()
  }
  get() {
    return this.tom.getValue()
  }
}

class SelectJsSingle extends SelectJs {
  constructor(id) {
    super()
    this.tom = new TomSelect(`#${id}`, {
      options: [{value: 1, text: 'Loading ...', disabled: true}],
      placeholder: 'All',
      hidePlaceholder: true,
      plugins: ['no_active_items', 'remove_button'],
      maxOptions: 999,
      onItemRemove: function() {
        if (this.getValue().length === 0) {
          // Fix for the remove_button plugin AND the squishening when out of focus.
          this.inputState()
        }
      }
    })
  }
  add(val) {
    this.tom.addItem(val)
  }
}

class SelectJsMultiple extends SelectJs {
  constructor(select) {
    super()
    const and = select.getAttribute('and')
    const placeholder = and === null ? 'or ...' : 'and ...'
    this.tom = new TomSelect(`#${select.id}`, {
      options: [{value: 1, text: 'Loading ...', disabled: true}],
      placeholder: 'All',
      hidePlaceholder: false,
      plugins: ['no_active_items', 'remove_button', 'caret_position', 'clear_button'],
      maxOptions: 999,
      onItemAdd: function() {
        this.settings.placeholder = placeholder
        // Tom-select expects that the user will want to keep adding similar options.
        this.setTextboxValue('')
        this.refreshOptions(false)
      },
      onItemRemove: function() {
        if (this.getValue().length === 0) {
          this.settings.placeholder = 'All'
          // Fix for the remove_button plugin.
          document.getElementById(`${select.id}-ts-control`).setAttribute('placeholder', 'All')
        }
      }
    })
  }
  add(vals) {
    for (const val of vals) {
      this.tom.addItem(val)
    }
  }
}

export { SelectJsSingle, SelectJsMultiple };
