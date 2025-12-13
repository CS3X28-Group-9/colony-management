# Style Guide

## Text Fields

- Use `CharField` for text whose length is limited by business logic.
- Use `TextField` for variable-length text.

## Choice Fields

- When defining a field with choices, the choices should be defined as a dictionary constant on the model class.
- The actual database values of a field's choices should be short, usually one character.

## HTML

- Do not construct Django form fields manually; instead, use the `attributes` attribute on the form fields.
- Do not use `<style>` blocks.

## Miscellaneous

- Use `model.id` instead of `model.pk`, unless working with external models where Pyright throws an error.
- Variable name lengths should be proportional to their scope. Very short names (around 1-3 characters) should be used very sparingly.
- Do not shadow methods with fields unless that field is a function with an appropriate signature.
