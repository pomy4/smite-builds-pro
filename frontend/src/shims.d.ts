// Without this TypeScript complained about not being able to find empty.png.
// Taken from some StackOverflow answer.
declare module "*.png" {
  const value: string;
  export default value;
}
