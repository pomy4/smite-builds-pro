<template>
    <div class="label-slider">
      <label class="label">{{ label }}</label>
      <div class="label-slider-column">
        <div class="slider-styled" :id="id" :format="format">Loading ...</div>
        <div class="label-slider-row">
          <div></div>
          -
          <div></div>
        </div>
      </div>
    </div>
</template>

<script>
export default {
  props: ['label', 'id', 'format']
}
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
.label-slider-row {
  display: flex;
  justify-content: space-between;
  padding: 0 1rem;
}
</style>
