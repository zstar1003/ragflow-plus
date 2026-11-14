# Management web app

This Vue app (`management/web`) is separate from the React chat UI in `web`.

## Language

Choose **English** or **简体中文** using the selector on the login page or in the top navigation bar. Chinese remains the default; the preference is saved in this browser and can be switched without signing out or reloading.

English currently covers user management (search, create/edit, delete, password reset, validation and confirmations), login, navigation labels and Element Plus controls. Other management pages and server-provided error messages are not translated by this change. Existing user data is never translated.

## Checks

Install the locked dependencies with `pnpm install --frozen-lockfile`, then run:

```sh
pnpm exec vue-tsc --noEmit
pnpm exec vitest run
pnpm exec vite build
```

The language tests use temporary browser storage and mocked management APIs. They do not modify real user accounts.
