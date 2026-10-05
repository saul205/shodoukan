#!/bin/sh
# Settings Keycloak can't take at startup, applied by the one-shot
# keycloak-setup service (deploy/compose.yml) after every start. Idempotent.
#
# - The shodoukan realm is invite-only: no self-registration.
# - Its clients' redirect URIs follow PUBLIC_URL. The realm file is only
#   imported once, so without this a realm created under another URL keeps
#   the old one.
# - The master realm (the admin console's sign-in) lives on the localhost
#   admin URL; on the public URL Caddy hides it.
#
# Environment: ADMIN_USER, ADMIN_PASSWORD, ADMIN_URL, PUBLIC_URL.

K=/opt/keycloak/bin/kcadm.sh
C=/tmp/kcadm.config

if ! $K config credentials --config "$C" --server http://keycloak:8080/idp \
    --realm master --user "$ADMIN_USER" --password "$ADMIN_PASSWORD" >/dev/null; then
  echo "WARNING: couldn't sign in to Keycloak (admin credentials changed?); skipping setup"
  exit 0
fi
set -e

client() {
  $K get clients --config "$C" -r shodoukan -q clientId="$1" --fields id --format csv --noquotes
}

$K update realms/shodoukan --config "$C" -s registrationAllowed=false

$K update "clients/$(client shodoukan-practice-web)" --config "$C" -r shodoukan \
  -s "redirectUris=[\"$PUBLIC_URL/*\"]" \
  -s "webOrigins=[\"$PUBLIC_URL\"]" \
  -s "attributes.\"post.logout.redirect.uris\"=$PUBLIC_URL/*"

$K update "clients/$(client shodoukan-practice-docs)" --config "$C" -r shodoukan \
  -s "redirectUris=[\"$PUBLIC_URL/practice-api/docs/oauth2-redirect\"]" \
  -s "webOrigins=[\"$PUBLIC_URL\"]"

# Last: it changes the master realm's issuer, which invalidates this
# session's token.
$K update realms/master --config "$C" -s "attributes.frontendUrl=$ADMIN_URL"

echo "Keycloak set up for $PUBLIC_URL (admin console on $ADMIN_URL)"
