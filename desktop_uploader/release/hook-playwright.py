# PyInstaller hook for playwright
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

# Collect all playwright related files
datas, binaries, hiddenimports = collect_all('playwright')

# Ensure playwright driver and browsers info are included
datas += collect_data_files('playwright')

# Add hidden imports for playwright internals
hiddenimports += [
    'playwright',
    'playwright.sync_api',
    'playwright.async_api',
    'playwright._impl',
    'playwright._impl._driver',
    'playwright._impl._connection',
    'playwright._impl._browser',
    'playwright._impl._browser_context',
    'playwright._impl._page',
    'playwright._impl._frame',
    'playwright._impl._element_handle',
    'playwright._impl._js_handle',
    'playwright._impl._network',
    'playwright._impl._input',
    'playwright._impl._download',
    'playwright._impl._video',
    'playwright._impl._console_message',
    'playwright._impl._dialog',
    'playwright._impl._file_chooser',
    'playwright._impl._helper',
    'playwright._impl._api_types',
    'playwright._impl._api_structures',
    'playwright._impl._assertions',
    'playwright._impl._locator',
    'playwright._impl._accessibility',
    'playwright._impl._cdp_session',
    'playwright._impl._artifact',
    'playwright._impl._stream',
    'playwright._impl._tracing',
    'playwright._impl._electron',
    'playwright._impl._errors',
    'playwright._impl._event_context_manager',
    'playwright._impl._fetch',
    'playwright._impl._greenlets',
    'playwright._impl._har_router',
    'playwright._impl._http_util',
    'playwright._impl._image_comparator',
    'playwright._impl._local_utils',
    'playwright._impl._object_factory',
    'playwright._impl._playwright',
    'playwright._impl._selectors',
    'playwright._impl._wait_helper',
    'greenlet',
    'pyee',
    'pyee.base',
    'pyee.asyncio',
    'websockets',
    'websockets.client',
    'websockets.server',
    'websockets.protocol',
    'websockets.connection',
]
