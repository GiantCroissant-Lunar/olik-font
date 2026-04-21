import {Config} from '@remotion/cli/config';

Config.setEntryPoint('./src/index.ts');
Config.setVideoImageFormat('png');
Config.setPixelFormat('yuv420p');

// The app's TS sources use `.js` import suffixes (ESM-style). Remotion's
// webpack bundler doesn't strip `.js` → `.tsx`/`.ts` by default, so we
// teach the resolver to try the TS extensions when a `.js` import is
// requested. Vitest handles this natively via resolve.alias (see
// vitest.config.ts).
Config.overrideWebpackConfig((config) => ({
  ...config,
  resolve: {
    ...config.resolve,
    extensionAlias: {
      ...((config.resolve as {extensionAlias?: Record<string, string[]>})
        ?.extensionAlias ?? {}),
      '.js': ['.js', '.ts', '.tsx'],
    },
  },
}));
