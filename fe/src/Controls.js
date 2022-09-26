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

import noUiSlider from 'nouislider';
import 'nouislider/dist/nouislider.css';
import wNumb from 'wnumb'

function parse_date(s) {
  const split = s.split('-')
  return Date.UTC(parseInt(split[0]), parseInt(split[1])-1, parseInt(split[2]))
}
function format_date(timestamp) {
  return new Date(parseInt(timestamp)).toISOString().split('T')[0]
}
function parse_time(s) {
  const split = s.split(':')
  return Date.UTC(0, 0, 1, parseInt(split[0]), parseInt(split[1]), parseInt(split[2]))
}
function format_time(timestamp) {
  return new Date(parseInt(timestamp)).toISOString().split('T')[1].split('.')[0]
}

class SliderJs {
  constructor(node) {
    this.node = node
  }
  init(range) {
    this.min = range[0]
    this.max = range[1]
    this.node.textContent = ''
    this.node.style.width = '6.667rem'
    this.node.style.margin = '0 1rem'
    this.tooltips = this.node.nextElementSibling.children
    const format = this.node.getAttribute('format')
    let options = {
      connect: true,
      animate: false,
    }
    if (format == 'date') {
      this.node.style.width = '12rem'
      this.min = parse_date(range[0])
      this.max = parse_date(range[1])
      options['step'] = 1000 * 60 * 60 * 24
      options['format'] = wNumb({decimals: 0})
      this.format = format_date
    } else if (format == 'time') {
      this.node.style.width = '9.3rem'
      this.min = parse_time(range[0])
      this.max = parse_time(range[1])
      options['step'] = 1000
      options['format'] = wNumb({decimals: 0})
      this.format = format_time
    } else {
      this.min = range[0]
      this.max = range[1]
      if (this.node.id == 'kda_ratio') {
        options['format'] = wNumb({decimals: 1})
        this.format = s => s.length < 4 ? `0${s}` : s
      } else {
        options['step'] = 1
        options['format'] = wNumb({decimals: 0})
        this.format = s => s.length < 2 ? `0${s}` : s
      }
    }
    options['start'] = [this.min, this.max]
    options['range'] = {'min': this.min, 'max': this.max}
    this.slider = noUiSlider.create(this.node, options)
    this.slider.on('update', (values, handle) => {
      this.tooltips[handle].textContent = this.format(values[handle]);
    });
  }
  clear() {
    this.slider.reset()
  }
  get() {
    const range = this.slider.get()
    return (range[0] > this.min || range[1] < this.max) ? [this.format(range[0]), this.format(range[1])] : []
  }
  add(range) {
    this.slider.set(range)
  }
}

export { SelectJsSingle, SelectJsMultiple, SliderJs };
