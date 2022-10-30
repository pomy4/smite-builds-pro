<template>
  <div class="label-select">
    <label class="label">{{ label }}</label>
    <select
      v-bind:id="id"
      autocomplete="on"
      v-bind:multiple="multiple"
      v-bind:and="and"
    ></select>
  </div>
</template>

<script>
export default {
  props: ["label", "id", "multiple", "and"],
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
