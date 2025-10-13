// Legacy backup re-export. The main WizardForm implementation now handles
// reference image steps and wizard flow; this backup simply forwards the export
// to avoid diverging logic while retaining the historical file path.
export { WizardForm } from './WizardForm';
