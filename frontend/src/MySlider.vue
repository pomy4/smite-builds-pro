<template>
  <div class="label-slider">
    <label v-bind:for="id" class="label">{{ label }}</label>
    <div class="label-slider-column">
      <div
        v-bind:id="id"
        ref="sliderElem"
        v-bind:style="{ width: helper.width() }"
        class="slider-styled"
      ></div>
      <div class="label-slider-row">
        <div>{{ tooltips[0] }}</div>
        -
        <div>{{ tooltips[1] }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, toRaw, watch } from "vue";
import noUiSlider, { API } from "nouislider";
import "nouislider/dist/nouislider.css";
import { SliderType } from "./types";
import { OtherProps, helperFactory } from "./my-slider-helper";

// Some of the comments in MySelect are also relevant here.

const props = defineProps<{
  id: string;
  label: string;
  current: string[];
  other: OtherProps;
}>();

const parseLimit = (): { N: [number, number]; S: [string, string] } => {
  if (props.other.unparsedLimit === null) {
    const defaultN = helper.default();
    const defaultS = helper.nToS(defaultN);
    return {
      N: [defaultN, defaultN],
      S: [defaultS, defaultS],
    };
  } else if (props.other.type === SliderType.Number) {
    return {
      N: props.other.unparsedLimit,
      S: [
        helper.nToS(props.other.unparsedLimit[0]),
        helper.nToS(props.other.unparsedLimit[1]),
      ],
    };
  } else {
    return {
      N: [
        helper.sToN(props.other.unparsedLimit[0]),
        helper.sToN(props.other.unparsedLimit[1]),
      ],
      S: props.other.unparsedLimit,
    };
  }
};

// I tried using computed (from Vue) here, so that this code doesn't have to be
// repeated in the watcher, but for some reason that caused the watcher to call
// itself recursively and I didn't want to spend the time to figure it out.
let helper = helperFactory(props.other);
let limit = parseLimit();

// Destructuring here so that changing tooltip doesn't change limit.
const tooltips = ref([...limit.S]);

const sliderElem = ref<HTMLElement | null>(null);
let slider: API | null = null;

const emit = defineEmits<{
  (e: "update:current", value: [string, string] | []): void;
}>();

const myEmit = (toBeEmitted: typeof lastEmit) => {
  lastEmit = toBeEmitted;
  emit("update:current", lastEmit);
};

let lastEmit: [string, string] | [] = [];

onMounted(() => {
  initSlider();
  updateSlider();
});

watch([() => props.other.type, () => props.other.unparsedLimit], () => {
  helper = helperFactory(props.other);
  limit = parseLimit();
  tooltips.value = [...limit.S];
  initSlider();
  myEmit([]);
});

watch(
  () => props.current,
  () => updateSlider()
);

const initSlider = () => {
  if (sliderElem.value === null) {
    throw Error("Illegal state");
  }

  if (slider !== null) {
    slider.destroy();
  }
  slider = noUiSlider.create(sliderElem.value, {
    connect: true,
    animate: false,
    format: {
      to: (n: number) => helper.nToS(n),
      from: (s: string) => helper.sToN(s),
    },
    // Not sure why start uses strings and range numbers.
    start: limit.S,
    range: {
      min: limit.N[0],
      max: limit.N[1],
    },
    step: helper.step(),
  });

  slider.on("update", (values, handle) => {
    tooltips.value[handle] = values[handle] as string;
  });
  slider.on("change", onChange);
};

type EventCallback = Parameters<API["on"]>[1];
const onChange: EventCallback = (values, handle) => {
  myEmit(
    values[handle] !== limit.S[handle] ? (values as [string, string]) : []
  );
};

const updateSlider = () => {
  if (slider === null) {
    throw Error("Illegal state");
  }

  if (toRaw(props.current) === lastEmit) {
    return;
  }

  const validatedCurrent: [string, number][] = [];
  for (const s of props.current) {
    try {
      const n = helper.sToN(s);
      if (isNaN(n)) {
        throw Error("NaN");
      }
      if (n < limit.N[0] || n > limit.N[1]) {
        throw Error("Out of range");
      }
      validatedCurrent.push([s, n]);
    } catch {
      console.log(`Slider ${props.id} filtered away ${s}!`);
    }
  }

  const normalizedCurrent = ((): [string, string] | [] => {
    if (validatedCurrent.length === 0) {
      return [];
    } else if (validatedCurrent.length === 1) {
      const s = validatedCurrent[0][0];
      console.log(`Slider ${props.id} filtered away ${s}!`);
      return [];
    } else {
      if (validatedCurrent.length > 2) {
        for (const [s] of validatedCurrent.slice(0, -2)) {
          console.log(`Slider ${props.id} filtered away ${s}!`);
        }
      }
      const [[bottomS, bottomN], [topS, topN]] = validatedCurrent.slice(-2);
      if (bottomN > topN || (bottomN === limit.N[0] && topN === limit.N[1])) {
        console.log(`Slider ${props.id} filtered away ${bottomS}!`);
        console.log(`Slider ${props.id} filtered away ${topS}!`);
        return [];
      } else {
        return [bottomS, topS];
      }
    }
  })();

  // Turning onChange off is not needed with nouislider, since calling the
  // reset and set functions doesn't fire the 'change' event, but the 'set'
  // event, but it is done anyway so that the code here is more similar
  // to the code in MySelect.
  slider.off("change");
  try {
    if (normalizedCurrent.length == 0) {
      slider.reset();
    } else {
      slider.set(normalizedCurrent);
    }
  } finally {
    slider.on("change", onChange);
  }

  if (normalizedCurrent.length != props.current.length) {
    myEmit(normalizedCurrent);
  }
};
</script>

<style>
.label:not(:last-child) {
  margin-bottom: unset;
}
.label-slider {
  display: flex;
  align-items: center;
  column-gap: 0.667rem;
}
.label-slider-column {
  display: flex;
  flex-direction: column;
  row-gap: 0.334rem;
}
.slider-styled {
  margin: 0 1rem;
}
.label-slider-row {
  display: flex;
  justify-content: space-between;
  padding: 0 1rem;
}
</style>
