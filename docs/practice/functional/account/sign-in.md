# Signing Up and Signing In

[← Functional documentation](../README.md)

How a user gets access to the practice app.

## Signing up and signing in

The practice app doesn't handle passwords itself. Signing up, signing in, "remember
me" and password resets happen on the **Shodoukan sign-in page**, run by the identity
provider (Keycloak). From the app, the user clicks **Sign in** and lands on that page,
where they can also create an account. After signing in, they're sent back to the app.

## The practice account

The first time a signed-in user uses the practice app, their **practice account is
created automatically**. There's no separate registration step. It starts with an
empty library, and their display name is their username on the sign-in page.

Everything in the practice app (library, collections, exercises) belongs to that
account. Nothing is shared between users.

## Sessions

A sign-in lasts a short time (minutes) and is renewed by the app in the background
while the user stays signed in on the sign-in page. When it can't be renewed, the
user is asked to sign in again.

Technical details: [authentication](../../technical/api/authentication.md).
