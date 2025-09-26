# InputForm Accessibility Review

## Summary
- Provide high-level recommendations for improving accessible labelling and status messaging without altering component APIs.

## Recommendations
- **Select labelling:** Replace the current `span.sr-only` elements with actual `<label>` elements linked to the `SelectTrigger` via `id` + `aria-labelledby` so assistive tech treats the prompt as a field label instead of generic text. Confirm the `SelectTrigger` receives a stable `id` (e.g., from `useId`) before wiring the association. This prevents the button role from lacking an accessible name when the placeholder is empty. See `frontend/src/components/InputForm.tsx` steps 2 and 3.
- **Textarea hint association:** For the "Perfil do cliente" and "Foco da campanha" textareas, ensure the hint copy (`<p id={...}>`) remains referenced through `aria-describedby` even after validation messaging is added so users hear both the guidance and any inline error text. Consider concatenating multiple ids when errors are present. See lines where `Textarea` components are defined in `InputForm.tsx`.
- **Loading feedback scope:** When the CTA button switches to "Gerando anúncios...", expose the status through an `aria-live="polite"` region adjacent to the form so screen readers receive progress updates even if focus stays on the disabled button. Keep the text identical to the visible copy to avoid duplicate wording. Review the submit button block near the end of `InputForm.tsx`.

These adjustments keep the visual design intact while ensuring each control announces a proper role, name, and state across screen readers.
