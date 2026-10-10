#!/usr/bin/env bash
# Creates the empty folder/file skeleton for server/ and client/
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p server/src/{config,models,controllers,routes,middleware,services,utils}
mkdir -p client/src/{assets,components,config,hooks,lib,pages,providers,schemas,services,styles,types,utils}
touch server/{.env,package.json} server/src/server.js server/src/config/db.js server/src/models/User.js
touch client/{tsconfig.json,vite.config.ts,package.json} client/src/{App.tsx,main.tsx} client/src/services/api.ts
