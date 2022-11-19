import TomSelect from "tom-select";
import "tom-select/dist/css/tom-select.css";

abstract class SelectJs {
  protected tom: TomSelect;
  constructor(tom: TomSelect, options: string[]) {
    this.tom = tom;
    const tom_options = options.map((option) => {
      return { value: option, text: option };
    });
    this.tom.removeOption("LOADING");
    this.tom.addOptions(tom_options);
    this.tom.refreshOptions(false);
  }
  clear() {
    this.tom.clear();
  }
  get() {
    return this.tom.getValue();
  }
}

class SelectJsSingle extends SelectJs {
  constructor(id: string, options: string[]) {
    const tom = new TomSelect(`#${id}`, {
      options: [{ value: "LOADING", text: "Loading ...", disabled: true }],
      placeholder: "All",
      hidePlaceholder: true,
      plugins: ["no_active_items", "remove_button"],
      maxOptions: 999,
      onItemRemove: function (this: TomSelect) {
        if (this.getValue().length === 0) {
          // Fix for the remove_button plugin
          // AND the squishening when out of focus.
          this.inputState();
        }
      },
    });
    super(tom, options);
  }
  add(val: string) {
    this.tom.addItem(val);
  }
}

class SelectJsMultiple extends SelectJs {
  constructor(select: Element, options: string[]) {
    const and = select.getAttribute("and");
    const placeholder = and === "false" ? "or ..." : "and ...";
    const tom = new TomSelect(`#${select.id}`, {
      options: [{ value: "LOADING", text: "Loading ...", disabled: true }],
      placeholder: "All",
      hidePlaceholder: false,
      plugins: [
        "no_active_items",
        "remove_button",
        "caret_position",
        "clear_button",
      ],
      maxOptions: 999,
      onItemAdd: function (this: TomSelect) {
        this.settings.placeholder = placeholder;
        // Tom-select expects that the user
        // will want to keep adding similar options.
        this.setTextboxValue("");
        this.refreshOptions(false);
      },
      onItemRemove: function (this: TomSelect) {
        if (this.getValue().length === 0) {
          this.settings.placeholder = "All";
          // Fix for the remove_button plugin.
          const controlId = `${select.id}-ts-control`;
          const controlElement = document.getElementById(controlId);
          if (controlElement === null) {
            console.log(
              "TomSelect remove_button plugin " +
                `workaround failed: ${controlId}`
            );
          } else {
            controlElement.setAttribute("placeholder", "All");
          }
        }
      },
    });
    super(tom, options);
  }
  add(vals: string[]) {
    for (const val of vals) {
      this.tom.addItem(val);
    }
  }
}

import noUiSlider, { API } from "nouislider";
import "nouislider/dist/nouislider.css";

class SliderJs {
  private min_s: string;
  private max_s: string;
  private slider: API;
  constructor(node: HTMLElement, range: [string, string] | [number, number]) {
    const type = node.getAttribute("type")!;
    const { width, n_to_s, s_to_n, min_s, max_s, min_n, max_n, step } =
      init_based_on_type(type, range);
    node.textContent = "";
    node.style.width = width;
    node.style.margin = "0 1rem";
    this.min_s = min_s;
    this.max_s = max_s;
    const options = {
      connect: true,
      animate: false,
      format: {
        to: n_to_s,
        from: s_to_n,
      },
      start: [min_s, max_s],
      range: {
        min: min_n,
        max: max_n,
      },
      step: step,
    };
    this.slider = noUiSlider.create(node, options);
    const tooltips = node.nextElementSibling!.children;
    this.slider.on("update", (values, handle) => {
      tooltips[handle].textContent = (values as string[])[handle];
    });
  }
  clear() {
    this.slider.reset();
  }
  get() {
    const [min_s, max_s] = this.slider.get() as string[];
    return min_s !== this.min_s || max_s !== this.max_s ? [min_s, max_s] : [];
  }
  add(range: [string, string]) {
    this.slider.set(range);
  }
}

function init_based_on_type(
  type: string,
  range: [string, string] | [number, number]
) {
  if (type == "date") {
    return init_date(range as [string, string]);
  } else if (type == "time") {
    return init_time(range as [string, string]);
  } else if (type.startsWith("number")) {
    const scale = Number(type.charAt(type.length - 1));
    return init_number(scale, range as [number, number]);
  } else {
    throw Error(`Unknown type: ${type}`);
  }
}

function init_date(range: [string, string]) {
  const width = "12rem";
  const n_to_s = date_num_to_str;
  const s_to_n = date_str_to_num;
  const [min_s, max_s] = range;
  const min_n = s_to_n(min_s);
  const max_n = s_to_n(max_s);
  const step = 1000 * 60 * 60 * 24;
  return { width, n_to_s, s_to_n, min_s, max_s, min_n, max_n, step };
}

function init_time(range: [string, string]) {
  const width = "9.3rem";
  const n_to_s = time_num_to_str;
  const s_to_n = time_str_to_num;
  const [min_s, max_s] = range;
  const min_n = s_to_n(min_s);
  const max_n = s_to_n(max_s);
  const step = 1000;
  return { width, n_to_s, s_to_n, min_s, max_s, min_n, max_n, step };
}

function init_number(scale: number, range: [number, number]) {
  const width = "6.667rem";
  const n_to_s = (n: number) =>
    n.toFixed(scale).padStart(scale === 0 ? 2 : 3 + scale, "0");
  const s_to_n = Number;
  const [min_n, max_n] = range;
  const min_s = n_to_s(min_n);
  const max_s = n_to_s(max_n);
  const step = 1 / (scale + 1);
  return { width, n_to_s, s_to_n, min_s, max_s, min_n, max_n, step };
}

function date_str_to_num(s: string) {
  const split = s.split("-");
  return Date.UTC(Number(split[0]), Number(split[1]) - 1, Number(split[2]));
}

function date_num_to_str(n: number) {
  return new Date(n).toISOString().split("T")[0];
}

function time_str_to_num(s: string) {
  const split = s.split(":");
  return Date.UTC(
    0,
    0,
    1,
    Number(split[0]),
    Number(split[1]),
    Number(split[2])
  );
}

function time_num_to_str(n: number) {
  return new Date(n).toISOString().split("T")[1].split(".")[0];
}

export { SelectJsSingle, SelectJsMultiple, SliderJs };
