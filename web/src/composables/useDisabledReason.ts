import { computed, type MaybeRefOrGetter, toValue } from "vue";
export function useDisabledReason(
  disabled: MaybeRefOrGetter<boolean>,
  reason: MaybeRefOrGetter<string>,
) {
  return computed(() =>
    toValue(disabled) ? toValue(reason) || "This action is currently unavailable." : "",
  );
}
