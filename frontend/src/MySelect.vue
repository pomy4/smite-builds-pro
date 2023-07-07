<template>
  <div class="label-select">
    <label v-bind:for="id" class="label">{{ label }}</label>
    <select
      v-bind:id="id"
      ref="selectElem"
      autocomplete="on"
      v-bind:multiple="multiple"
    ></select>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed, toRaw } from "vue";
import TomSelect from "tom-select";
import "tom-select/dist/css/tom-select.css";

const props = defineProps<{
  label: string;
  id: string;
  items: string[];
  options: string[] | number[] | boolean[] | null;
  multiple?: boolean;
  and?: boolean;
}>();

const selectElem = ref<HTMLInputElement | null>(null);
let select: TomSelect | null = null;

let stringifiedOptions: string[] = [];

const defaultPlaceholder = "All";
const placeholder = computed(() => (props.and ? "and ..." : "or ..."));

const emit = defineEmits<{
  (e: "update:items", value: string[]): void;
}>();

const myEmit = (toBeEmitted: typeof lastEmit) => {
  lastEmit = toBeEmitted;
  emit("update:items", lastEmit);
};

let lastEmit: string[] = [];

onMounted(() => {
  initSelect();
  // Currently selects get initialized with empty items, but
  // this is still needed to make hot reload work (when updating this component)
  // (state stays the same, so the watcher doesn't get triggered).
  updateSelect();
});

// These watchers are activated only when the whole the object changes,
// and not when it is just modified, but we don't mind that.

// This is (currently) only called
// when the options are received from the backend.
watch(
  () => props.options,
  () => {
    initSelect();
    myEmit([]);
  }
);

// This is (currently) only called
// 1) on a new page when the URL query params contain control state
// 2) when the Clear button is clicked
// 3) after superfluous emit calls
watch(
  () => props.items,
  () => updateSelect()
);

const initSelect = () => {
  if (selectElem.value === null) {
    throw Error("Illegal state");
  }

  let tomOptions: { value: string; text: string; disabled?: boolean }[];
  if (props.options === null) {
    stringifiedOptions = [];
    tomOptions = [{ value: "LOADING", text: "Loading ...", disabled: true }];
  } else {
    stringifiedOptions = props.options.map((option) => option.toString());
    tomOptions = stringifiedOptions.map((option) => ({
      value: option,
      text: option,
    }));
  }

  const sharedSettings = {
    options: tomOptions,
    maxOptions: 999,
    placeholder: defaultPlaceholder,
  };
  const moreSettings = (() => {
    if (!props.multiple) {
      return {
        hidePlaceholder: true,
        plugins: ["no_active_items", "remove_button"],
      };
    } else {
      return {
        hidePlaceholder: false,
        plugins: [
          "no_active_items",
          "remove_button",
          "caret_position",
          "clear_button",
        ],
      };
    }
  })();

  if (select !== null) {
    select.destroy();
  }
  select = new TomSelect(selectElem.value, {
    ...sharedSettings,
    ...moreSettings,
  });
  select.on("change", onChange);

  if (!props.multiple) {
    select.on("item_remove", function (this: TomSelect) {
      // Fix for the remove_button plugin
      // AND the squishening when out of focus.
      // UPDATE: I tried removing this, and nothing seemed to go wrong.
      this.inputState();
    });
  } else {
    select.on("item_add", function (this: TomSelect) {
      this.settings.placeholder = placeholder.value;
      // Tom-select expects that the user
      // will want to keep adding similar options.
      this.setTextboxValue("");
      this.refreshOptions(false);
    });
    select.on("item_remove", function (this: TomSelect) {
      if (this.getValue().length === 0) {
        this.settings.placeholder = defaultPlaceholder;
        // Fix for the remove_button plugin.
        const controlId = `${props.id}-ts-control`;
        const controlElement = document.getElementById(controlId);
        if (controlElement === null) {
          console.log(
            "TomSelect remove_button plugin " +
              `workaround failed: ${controlId}`
          );
        } else {
          controlElement.setAttribute("placeholder", defaultPlaceholder);
        }
      }
    });
  }
};

const onChange = (value: string | string[]) => {
  if (typeof value === "string") {
    myEmit(value ? [value] : []);
  } else {
    // This doesn't activate the watcher, since props.items will be
    // the same object, but we don't mind that.
    myEmit(value);
  }
};

const updateSelect = () => {
  if (select === null) {
    throw Error("Illegal state");
  }

  // If this was called just because we just emitted new items,
  // we don't need to do anything.
  // toRaw is needed since Vue returns some kind of proxy.
  if (toRaw(props.items) === lastEmit) {
    return;
  }

  const validatedItems: string[] = [];
  for (const item of props.items) {
    if (stringifiedOptions.includes(item)) {
      validatedItems.push(item);
    } else {
      console.log(`Select ${props.id} filtered away ${item}!`);
    }
  }

  const normalizedItems = (() => {
    if (props.multiple) {
      return validatedItems;
    } else {
      if (validatedItems.length > 1) {
        for (const item of validatedItems.slice(0, -1)) {
          console.log(`Select ${props.id} filtered away ${item}!`);
        }
      }
      return validatedItems.slice(-1);
    }
  })();

  // Turn onChange off while we are changing
  // the select manually to avoid extraneous calls.
  select.off("change");
  // There shouldn't be any exceptions here, but just to make sure.
  try {
    select.clear();
    for (const item of normalizedItems) {
      select.addItem(item);
    }
  } finally {
    select.on("change", onChange);
  }

  if (normalizedItems.length != props.items.length) {
    myEmit(normalizedItems);
  }
};
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
</style>
